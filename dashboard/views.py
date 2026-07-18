import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import (Avg, Count, DecimalField, F, Q, Sum)
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from payments.constants import PAYMENT_STATUS_PAID
from payments.models import YouPayTransactionData

DEFAULT_RANGE_DAYS = 30
TOP_N = 10

# Statuses that represent a payment error/failure (excludes customer/merchant
# initiated cancelled/expired/voided).
FAILURE_STATUSES = ['declined', 'failed', 'rejected', 'error',
                    'declined_retry', 'rejected_retry']

# Failure-reason buckets, matched against response_summary in order (first match
# wins). Keep the blank check first; 'Other' is the catch-all.
FAILURE_CATEGORY_RULES = [
    ('Risk / Fraud block', r'risk|fraud|suspected|security'),
    ('Issuer decline (bank)',
     r'declined by bank|do not honou?r|contact your bank|retry with another'),
    ('Card data / CVV / expiry',
     r'cvv|track data|invalid card|card number|expired card|expiry'),
    ('Invalid Transaction', r'invalid transaction'),
    ('Operation not allowed: CAPTURE', r'operation not allowed|capture'),
    ('3DS not enabled / malfunction', r'3ds|3d secure'),
    ('Card restricted / funds / limits',
     r'restricted card|insufficient|exceeds|withdrawal|limit'),
    ('Timeout / dropped / in review',
     r'timeout|too late|dropped|review|malfunction'),
    ('Generic failed / declined',
     r'payment failed|transaction declined|payment declined'),
]
_COMPILED_RULES = [(label, re.compile(pat, re.I))
                   for label, pat in FAILURE_CATEGORY_RULES]
BLANK_CATEGORY = 'Blank (no reason captured)'
OTHER_CATEGORY = 'Other'


def categorize_failure(summary):
    """Map a raw response_summary string to an actionable failure category."""
    if not summary or not summary.strip():
        return BLANK_CATEGORY
    for label, rx in _COMPILED_RULES:
        if rx.search(summary):
            return label
    return OTHER_CATEGORY

# Prefer the AED-normalised amount, fall back to the raw order amount.
MONEY = Coalesce(
    F('amount_in_aed'), F('amount'),
    output_field=DecimalField(max_digits=18, decimal_places=4),
)
PAID = Q(payment_status=PAYMENT_STATUS_PAID)


def _parse_date(value):
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _pct(value, total):
    if not total:
        return 0
    return round((value or 0) / total * 100, 1)


def _with_bar(rows, key='count'):
    """Attach a bar width (relative to the largest row) for CSS bar charts."""
    rows = list(rows)
    biggest = max((r.get(key) or 0 for r in rows), default=0)
    for row in rows:
        row['bar'] = _pct(row.get(key) or 0, biggest)
    return rows


# Canonicalise the free-text payment_scheme values (Visa/VISA, Amex/American
# Express, etc.) into clean labels for the chart.
_SCHEME_ALIASES = {
    'visa': 'Visa',
    'mastercard': 'Mastercard',
    'mada': 'mada',
    'amex': 'Amex', 'american express': 'Amex',
    'paypal': 'PayPal',
}


def _normalize_scheme(value):
    if not value or not value.strip() or value.strip().lower() == 'none':
        return 'None / unknown'
    return _SCHEME_ALIASES.get(value.strip().lower(), value.strip())


def _scheme_breakdown(qs):
    """Aggregate payment_scheme with case/alias normalisation, ranked desc."""
    merged = {}
    for row in qs.values('payment_scheme').annotate(count=Count('id')):
        merged[_normalize_scheme(row['payment_scheme'])] = \
            merged.get(_normalize_scheme(row['payment_scheme']), 0) + row['count']
    rows = [{'scheme': k, 'count': v} for k, v in merged.items()]
    rows.sort(key=lambda r: r['count'], reverse=True)
    return _with_bar(rows)


@method_decorator(staff_member_required, name='dispatch')
class DashboardView(TemplateView):
    """Landing page for the dashboard section."""
    template_name = 'dashboard/index.html'


@method_decorator(staff_member_required, name='dispatch')
class MonitoringView(TemplateView):
    template_name = 'dashboard/monitoring.html'

    def get_range(self):
        today = timezone.localdate()
        end = _parse_date(self.request.GET.get('end')) or today
        start = _parse_date(self.request.GET.get('start'))
        if not start:
            start = end - datetime.timedelta(days=DEFAULT_RANGE_DAYS - 1)
        if start > end:
            start, end = end, start
        return start, end

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start, end = self.get_range()

        qs = YouPayTransactionData.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end)

        totals = qs.aggregate(
            total_count=Count('id'),
            total_volume=Sum(MONEY),
            paid_count=Count('id', filter=PAID),
            paid_volume=Sum(MONEY, filter=PAID),
            fraud_count=Count('id', filter=Q(is_fraud=True)),
            flagged_count=Count('id', filter=Q(is_flagged=True)),
            avg_amount=Avg(MONEY),
        )
        total_count = totals['total_count'] or 0

        # Daily trend, gap-filled so the chart is continuous.
        trend_map = {
            row['day']: row for row in
            qs.annotate(day=TruncDate('created_at')).values('day').annotate(
                count=Count('id'), volume=Sum(MONEY)).order_by('day')
        }
        trend = []
        day = start
        while day <= end:
            row = trend_map.get(day, {})
            trend.append({
                'day': day,
                'count': row.get('count') or 0,
                'volume': row.get('volume') or 0,
            })
            day += datetime.timedelta(days=1)
        trend = _with_bar(trend, key='count')

        # Breakdown: by gateway (with success rate).
        by_gateway = list(
            qs.values('payment_gateway').annotate(
                count=Count('id'), volume=Sum(MONEY),
                paid=Count('id', filter=PAID)).order_by('-count'))
        for row in by_gateway:
            row['success_rate'] = _pct(row['paid'], row['count'])
        by_gateway = _with_bar(by_gateway, key='count')

        by_client = _with_bar(
            qs.values('api_client__name').annotate(
                count=Count('id'), volume=Sum(MONEY)
            ).order_by('-count')[:TOP_N])

        by_country = _with_bar(
            qs.values('country_code').annotate(
                count=Count('id'), volume=Sum(MONEY)
            ).order_by('-count')[:TOP_N])

        by_method = _with_bar(
            qs.values('payment_method').annotate(
                count=Count('id')).order_by('-count')[:TOP_N])

        by_status = _with_bar(
            qs.values('payment_status').annotate(
                count=Count('id')).order_by('-count'))

        by_scheme = _scheme_breakdown(qs)

        # Alert: payment methods that were attempted but have zero paid txns
        # in the selected range (a method that is not converting at all).
        method_conversion = qs.values('payment_method').annotate(
            total=Count('id'), paid=Count('id', filter=PAID)).order_by('-total')
        unpaid_method_alerts = [
            {'method': r['payment_method'], 'total': r['total']}
            for r in method_conversion
            if r['paid'] == 0 and r['total'] > 0
            and (r['payment_method'] or '').strip().lower() not in ('', 'none')
        ]

        context.update({
            'start': start,
            'end': end,
            'totals': totals,
            'success_rate': _pct(totals['paid_count'], total_count),
            'fraud_rate': _pct(totals['fraud_count'], total_count),
            'flagged_rate': _pct(totals['flagged_count'], total_count),
            'trend': trend,
            'by_gateway': by_gateway,
            'by_client': by_client,
            'by_country': by_country,
            'by_method': by_method,
            'by_status': by_status,
            'by_scheme': by_scheme,
            'unpaid_method_alerts': unpaid_method_alerts,
        })
        return context


@method_decorator(staff_member_required, name='dispatch')
class FailuresView(TemplateView):
    """Monitor gateway failure reasons, ranked by volume."""
    template_name = 'dashboard/failures.html'

    def get_range(self):
        today = timezone.localdate()
        end = _parse_date(self.request.GET.get('end')) or today
        start = _parse_date(self.request.GET.get('start'))
        if not start:
            start = end - datetime.timedelta(days=DEFAULT_RANGE_DAYS - 1)
        if start > end:
            start, end = end, start
        return start, end

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start, end = self.get_range()

        in_range = YouPayTransactionData.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end)
        total_txns = in_range.count()

        failures = in_range.filter(payment_status__in=FAILURE_STATUSES)
        total_failures = failures.count()

        # Pull raw (summary, gateway, count) groups and bucket in Python so the
        # categorisation rules live in one readable place.
        gateways = set()
        cat_totals = {}          # category -> count
        cat_by_gw = {}           # category -> {gateway -> count}
        rows = failures.values('response_summary', 'payment_gateway').annotate(
            count=Count('id'))
        for row in rows:
            cat = categorize_failure(row['response_summary'])
            gw = row['payment_gateway'] or '—'
            gateways.add(gw)
            n = row['count']
            cat_totals[cat] = cat_totals.get(cat, 0) + n
            cat_by_gw.setdefault(cat, {})[gw] = \
                cat_by_gw.setdefault(cat, {}).get(gw, 0) + n

        gateways = sorted(gateways)
        biggest = max(cat_totals.values(), default=0)
        categories = []
        for cat, count in sorted(cat_totals.items(),
                                 key=lambda kv: kv[1], reverse=True):
            categories.append({
                'label': cat,
                'count': count,
                'pct': _pct(count, total_failures),
                'bar': _pct(count, biggest),
                'is_blank': cat == BLANK_CATEGORY,
                'by_gateway': [
                    {'gateway': gw, 'count': cat_by_gw[cat].get(gw, 0)}
                    for gw in gateways],
            })

        context.update({
            'start': start,
            'end': end,
            'total_txns': total_txns,
            'total_failures': total_failures,
            'failure_rate': _pct(total_failures, total_txns),
            'gateways': gateways,
            'categories': categories,
        })
        return context


# Response-summary signature for transactions blocked by the risk engine.
RISK_BLOCK_REGEX = r'risk|fraud|suspected|security'


@method_decorator(staff_member_required, name='dispatch')
class RiskEngineView(TemplateView):
    """Monitor risk-engine signals: flagged, fraud and risk-blocked txns."""
    template_name = 'dashboard/risk_engine.html'

    def get_range(self):
        today = timezone.localdate()
        end = _parse_date(self.request.GET.get('end')) or today
        start = _parse_date(self.request.GET.get('start'))
        if not start:
            start = end - datetime.timedelta(days=DEFAULT_RANGE_DAYS - 1)
        if start > end:
            start, end = end, start
        return start, end

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start, end = self.get_range()

        qs = YouPayTransactionData.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end)

        risk_q = Q(response_summary__iregex=RISK_BLOCK_REGEX)
        totals = qs.aggregate(
            total_count=Count('id'),
            flagged_count=Count('id', filter=Q(is_flagged=True)),
            fraud_count=Count('id', filter=Q(is_fraud=True)),
            blocked_count=Count('id', filter=risk_q),
        )
        total_count = totals['total_count'] or 0

        # Daily trend of flagged transactions, gap-filled.
        trend_map = {
            row['day']: row['count'] for row in
            qs.filter(is_flagged=True).annotate(day=TruncDate('created_at'))
            .values('day').annotate(count=Count('id')).order_by('day')
        }
        trend = []
        day = start
        while day <= end:
            trend.append({'day': day, 'count': trend_map.get(day, 0)})
            day += datetime.timedelta(days=1)
        trend = _with_bar(trend, key='count')

        # Risk by gateway (flagged / fraud / blocked, with flagged rate).
        by_gateway = list(qs.values('payment_gateway').annotate(
            total=Count('id'),
            flagged=Count('id', filter=Q(is_flagged=True)),
            fraud=Count('id', filter=Q(is_fraud=True)),
            blocked=Count('id', filter=risk_q)).order_by('-flagged'))
        for row in by_gateway:
            row['flagged_rate'] = _pct(row['flagged'], row['total'])
        by_gateway = _with_bar(by_gateway, key='flagged')

        # Risk by country (top by flagged).
        by_country = _with_bar(list(qs.values('country_code').annotate(
            flagged=Count('id', filter=Q(is_flagged=True)),
            fraud=Count('id', filter=Q(is_fraud=True))
        ).order_by('-flagged')[:TOP_N]), key='flagged')

        # Top risk-block reasons (from response_summary).
        top_reasons = _with_bar(list(
            qs.filter(risk_q).exclude(response_summary__isnull=True)
            .exclude(response_summary='')
            .values('response_summary').annotate(count=Count('id'))
            .order_by('-count')[:TOP_N]))

        # Most recent flagged / fraud transactions.
        recent = list(qs.filter(Q(is_flagged=True) | Q(is_fraud=True))
                      .order_by('-created_at')
                      .values('transaction_id', 'created_at', 'amount',
                              'currency', 'payment_gateway', 'country_code',
                              'payment_status', 'is_fraud', 'is_flagged')[:15])

        context.update({
            'start': start,
            'end': end,
            'totals': totals,
            'flagged_rate': _pct(totals['flagged_count'], total_count),
            'fraud_rate': _pct(totals['fraud_count'], total_count),
            'blocked_rate': _pct(totals['blocked_count'], total_count),
            'trend': trend,
            'by_gateway': by_gateway,
            'by_country': by_country,
            'top_reasons': top_reasons,
            'recent': recent,
        })
        return context

ARG BASE_IMAGE

FROM $BASE_IMAGE

ARG ENVIRONMENT

ADD ./${ENVIRONMENT}/templates /ygag/nginx/templates
COPY ./${ENVIRONMENT}/nginx.conf /ygag/nginx/conf/nginx.conf

# Overwrite default one
COPY entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh
CMD ./entrypoint.sh

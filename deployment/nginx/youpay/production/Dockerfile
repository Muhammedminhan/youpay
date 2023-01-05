FROM 459037613883.dkr.ecr.ap-south-1.amazonaws.com/production/ygag/custom/nginx:1.16.1-1

ADD ./templates /ygag/nginx/templates
COPY nginx.conf /ygag/nginx/conf/nginx.conf

# Overwrite default one
COPY entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh
CMD ./entrypoint.sh

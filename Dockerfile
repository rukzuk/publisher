# based on ubuntu 18.04 (bionic)
FROM phusion/baseimage:0.11

# proposed breaks some packages (e.g. php-intl)
RUN rm -rf /etc/apt/sources.list.d/proposed.list

# phusion/baseimage is not always up to date. :-(
RUN apt-get update  && \
    apt-get dist-upgrade -y --no-install-recommends

# Set Timezone
RUN echo "Europe/Berlin" > /etc/timezone

# Install Depencies
RUN apt-get install -y --no-install-recommends \
        tzdata \
        sudo

RUN dpkg-reconfigure --frontend noninteractive tzdata

# Make Debian/Ubuntu and Docker friends
ENV DEBIAN_FRONTEND noninteractive


### BEGIN

# install phyton and pip
RUN apt-get install -y --no-install-recommends \
        build-essential \
        python3 \
        python3-dev \
        python3-pip \
        python3-setuptools \
        redis

# python stuff with modules
#RUN apt-get install -y --no-install-recommends \
#        gunicorn3 \
#        python3-paramiko \
#        supervisor

# Add users and folders
RUN useradd -s /bin/bash -d /opt/publisher publisher
RUN mkdir -p /var/log/publisher
RUN chown publisher /var/log/publisher
RUN mkdir -p /var/tmp/publisher
RUN chown publisher /var/tmp/publisher

# copy code
RUN mkdir -p /opt/publisher
COPY . /opt/publisher
# remove dev config file
RUN rm /opt/publisher/settings-dev.ini 2>/dev/null
# fix rights
RUN chown -R publisher /opt/publisher

# install requirements
RUN pip3 install -r /opt/publisher/requirements.txt

# Activate services in runit
RUN mkdir -p /etc/service/supervisord
COPY conf/supervisord.runit /etc/service/supervisord/run
RUN chmod +x /etc/service/supervisord/run

RUN mkdir -p /etc/service/redis
COPY conf/redis.runit /etc/service/redis/run
RUN chmod +x /etc/service/redis/run

### END

# Remove unused packages (only used to build)  & Cleanup
RUN apt-get purge -y build-essential
RUN apt-get clean -y
RUN apt-get autoremove -y
RUN rm -rf /var/lib/apt/lists/*

EXPOSE 8000



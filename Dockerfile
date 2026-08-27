FROM 192.168.1.125:5000/raspberrypios/bullseye:20231205

# No apt upgrade — slow/fragile on Pi CI; snapshot base is enough for the runtime image.
RUN apt-get -o Acquire::ForceIPv4=true update -qqy \
    && apt-get -o Acquire::ForceIPv4=true install -qqy --no-install-recommends python3 wget zip git \
    && apt-get clean

COPY cleep.deb .
# Keep/refresh apt lists for Depends; purge timesyncd (conflicts with ntp).
RUN apt-get -o Acquire::ForceIPv4=true update -qqy \
    && DEBIAN_FRONTEND=noninteractive apt-get purge -y systemd-timesyncd 2>/dev/null || true \
    && CLEEP_ENV=ci apt-get -o Acquire::ForceIPv4=true install -qyf ./cleep.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f ./cleep.deb
RUN systemctl disable cleep || true

RUN python3 -m pip install -q cleepcli
RUN mkdir -p /tmp/cleep-dev/modules && REPO_DIR=/tmp/cleep-dev cleep-cli cigetmods && rm -rf /tmp/cleep-dev

RUN cleep --stdout --noro --dryrun > cleep.log 2>&1 || (cat cleep.log; false)
RUN cat cleep.log && rm cleep.log

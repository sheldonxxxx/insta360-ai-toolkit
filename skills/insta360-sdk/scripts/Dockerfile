FROM ubuntu:22.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    g++ python3 libegl1 libgl1 libglx0 libglvnd0 libgtk-3-0 libtiff5 libharfbuzz0b \
    libglfw3 libvulkan1 libopenblas0 libdc1394-25 libgomp1 libgl1-mesa-dri mesa-utils xvfb xauth \
    && rm -rf /var/lib/apt/lists/*
ENV LC_ALL=C.UTF-8
WORKDIR /work

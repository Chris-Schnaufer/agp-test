FROM ubuntu:18.04
LABEL maintainer="Chris Schnaufer <schnaufer@email.arizona.edu>"

# Install any programs needed
RUN useradd -u 49044 extractor \
    && mkdir /home/extractor

RUN chown -R extractor /home/extractor \
    && chgrp -R extractor /home/extractor 

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        libgdal-dev \
        gcc \
        g++ \
        python3 \
        python3-pip \
        python3-dev \
        python3-gdal \
        gdal-bin
      
RUN python3 -m pip install --upgrade --no-cache-dir pip 

RUN python3 -m pip install --upgrade --no-cache-dir setuptools && \
    python3 -m pip install --upgrade --no-cache-dir \
        influxdb \
        laspy \
        requests==2.21.0 \
        python-dateutil \
        utm \
        netCDF4 \
        matplotlib \
        Pillow \
        scipy \
        pygdal==2.2.3.5 \
        pyclowder
#        terraref-stereo-rgb

RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY terraref/ /home/extractor/terraref/
COPY terrautils/ /home/extractor/terrautils/

COPY *.py /home/extractor/
RUN chmod +x /home/extractor/bin2tif.py

USER extractor
ENTRYPOINT ["/home/extractor/bin2tif.py"]

ENV \
    PYTHONPATH="${PYTHONPATH}:/home/extractor/terrautils"

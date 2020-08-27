FROM ubuntu:16.04

MAINTAINER Name <hardeep.nahal@oicr.on.ca>

RUN apt-get update && apt-get install -y git && apt-get install -y wget

RUN apt-get update && apt-get install -y software-properties-common && apt-get install -y python-software-properties

RUN \
  apt-add-repository ppa:openjdk-r/ppa && \
  apt-get update && \
  apt install -y openjdk-11-jdk && \
  apt-get clean;

# Workaround to deal with the "java.security.InvalidAlgorithmParameterException: the trustAnchors parameter must be non-empty" error using OpenJDK 11: 
# Save an empty JKS file with the default 'changeit' password for Java cacerts.
RUN \
  /usr/bin/printf '\xfe\xed\xfe\xed\x00\x00\x00\x02\x00\x00\x00\x00\xe2\x68\x6e\x45\xfb\x43\xdf\xa4\xd9\x92\xdd\x41\xce\xb6\xb2\x1c\x63\x30\xd7\x92' > /etc/ssl/certs/java/cacerts && \
# Re-add all the CA certs into the previously empty file.
  /var/lib/dpkg/info/ca-certificates-java.postinst configure

ENV JAVA_HOME /usr/lib/jvm/java-11-openjdk-amd64/bin/java

RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update
RUN apt-get install -y python3.6
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.5 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 2
RUN update-alternatives --config python3

RUN apt-get install -y python3-pip
RUN pip3 install dataclasses==0.3

RUN pip3 install overture-song

RUN mkdir /score-client
RUN wget -O score-client.tar.gz https://artifacts.oicr.on.ca/artifactory/dcc-release/bio/overture/score-client/[RELEASE]/score-client-[RELEASE]-dist.tar.gz
RUN  tar xvzf score-client.tar.gz -C /score-client --strip-components=1

RUN echo "accessToken=\$ACCESSTOKEN" > /score-client/conf/application.properties
RUN echo "storage.url=\${STORAGEURL}" >> /score-client/conf/application.properties
RUN echo "metadata.url=\${METADATAURL}" >> /score-client/conf/application.properties
RUN echo "logging.file=./storage-client.log" >> /score-client/conf/application.properties
RUN echo "logging.level.bio.overture.score=DEBUG" >> /score-client/conf/application.properties
RUN echo "logging.level.org.springframework.retry=TRACE" >> /score-client/conf/application.properties
RUN echo "logging.level.org.springframework.web=DEBUG" >> /score-client/conf/application.properties
RUN echo "logging.level.com.amazonaws.services=TRACE" >> /score-client/conf/application.properties
RUN echo "storage.retryNumber=30" >> /score-client/conf/application.properties
RUN echo "transport.memory=5" >> /score-client/conf/application.properties
RUN echo "client.connectTimeoutSeconds=999999" >> /score-client/conf/application.properties
RUN echo "client.readTimeoutSeconds=999999" >> /score-client/conf/application.properties

RUN mkdir /scripts
RUN wget https://raw.githubusercontent.com/icgc-dcc/dckr_song_upload/master/tools/upload_with_song.py -O /scripts/upload

RUN chmod +x /scripts/upload

ENV PATH="/scripts/:${PATH}"
ENV PATH="/score-client/bin:${PATH}"

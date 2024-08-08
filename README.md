# Circular Drive Initiative - Grading Toolkit
Circular Drive Initiative - Open Source Storage Device Grading Toolkit.

#### Operating Systems

[![linux](https://img.shields.io/badge/Debian-A81D33?style=flat&logo=debian&logoColor=white)](https://www.debian.com)
[![linux](https://img.shields.io/badge/Ubuntu-E95420?style=flat&logo=ubuntu&logoColor=white)](https://www.ubuntu.com)

#### Programming Languages

[![python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)

### Getting Started

This software requires the following to launch:

* Linux GNU x86/x86
* Python 3.12

#### Required 3rd Party Software
```sh
# Install Pre-Requisites
apt install wget gcc meson

# nvme-cli - https://github.com/linux-nvme/nvme-cli
apt install nvme-cli

# sg3-utils - https://sg.danny.cz/sg/sg3_utils.html
apt install sg3-utils

# openseachest - https://github.com/Seagate/openSeaChest
git clone --recurse-submodules --branch develop https://github.com/Seagate/openSeaChest.git openSeaChest-develop
cd openSeahChest-develop
meson --buildtype=release builddir
ninja -C builddir

# smartmontools - https://www.smartmontools.org/
wget https://downloads.sourceforge.net/project/smartmontools/smartmontools/7.4/smartmontools-7.4.tar.gz && \
  tar zxvf smartmontools-7.4.tar.gz && \
  cd smartmontools-7.4 && \
  ./configure && \
  make && \
  make install && \
  smartctl;

# hdsentinel - https://www.hdsentinel.com/
wget https://www.hdsentinel.com/hdslin/hdsentinel-019c-x64.gz && \
  gunzip hdsentinel-019c-x64.gz && \
  chmod 777 hdsentinel-019c-x64 && \
  mv hdsentinel-019c-x64 /usr/local/sbin/hdsentinel && \
  hdsentinel;

# Install hdparm - https://github.com/Distrotech/hdparm/tree/master
wget https://sourceforge.net/projects/hdparm/files/hdparm/hdparm-9.65.tar.gz && \
  tar zxvf hdparm-9.65.tar.gz && \
  cd hdparm-9.65 && \
  make install && \
  hdparm;
```

#### Install Dependencies
```shell
pip install -r requirements.txt

# This will install the following:
- xmltodict
```

### Execution
```shell
# Go to CDI Grading Tool Directory
cd cdi-grading-tool-alpha;

# Create folder for Logs
mkdir logs

# Launch Console 
python3 main.py;
```

## Roadmap
- [ ] Add full change logs.

## License
* TODO ...

## Acknowledgments
* TODO...

## Contact
* Jonmichael Hands - CDI/Chia - jmhands@chia.net
* Nick Hayhurst - Interact/Cedar - nick.hayhurst@interactdc.com

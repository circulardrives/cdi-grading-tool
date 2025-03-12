# Circular Drive Initiative - Grading Toolkit
Circular Drive Initiative - Open Source Storage Device Grading Toolkit.

#### Operating Systems

[![linux](https://img.shields.io/badge/Debian-A81D33?style=flat&logo=debian&logoColor=white)](https://www.debian.com)
[![linux](https://img.shields.io/badge/Ubuntu-E95420?style=flat&logo=ubuntu&logoColor=white)](https://www.ubuntu.com)

#### Programming Languages

[![python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)

### Getting Started

This software requires the following to launch:

* Linux GNU x86/x64
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
cd openSeaChest-develop
meson --buildtype=release builddir
ninja -C builddir
cd builddir
cp openSeaChest_* !(*.p) /usr/bin/openSeaChest/

# smartmontools - https://www.smartmontools.org/
wget https://downloads.sourceforge.net/project/smartmontools/smartmontools/7.4/smartmontools-7.4.tar.gz && \
  tar zxvf smartmontools-7.4.tar.gz && \
  cd smartmontools-7.4 && \
  ./configure && \
  make && \
  make install && \
  smartctl;
```

### Execution
```shell
# Go to CDI Grading Tool Directory
cd cdi-grading-tool-alpha

# Create a Virtual Environment
python3 -m venv .venv

# Activate the Virtual Environment
source .venv/bin/activate

# Upgrade Pip
pip install --upgrade pip

# Install CDI Grading Tool
pip install -e .

# Create Logs Folder
mkdir logs

# Launch Example - super user permissions required
python3 example.py
```

## Roadmap
- [ ] Add full change logs.

## Change Logs
* TODO ...

## License
* TODO ...

## Acknowledgments
* TODO...

## Contact
* Jonmichael Hands - CDI/Chia - jmhands@chia.net
* Nick Hayhurst - Interact/Cedar - nick.hayhurst@interactdc.com

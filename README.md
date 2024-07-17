# Circular Drive Initiative - Grading Toolkit
Circular Drive Initiative - Open Source Storage Device Grading Toolkit.

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

### Architecture

[![linux](https://img.shields.io/badge/Linux-Debian_12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![python](https://img.shields.io/badge/PySide-6-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)

## Getting Started

### Prerequisites
This software requires the following to launch:

* Linux GNU x86/x86
* Python 3.12

#### Required Software
```sh
# Become Root
sudo su;

# Standard Tools
apt install lshw fio lsscsi blktool sg3-utils nvme-cli; 

# openSeaChest - https://github.com/Seagate/openSeaChest
apt install openseachest;

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

#### Virtual Environment
```shell
# Install Virtualenv
pip install virtualenv

# Create Virtualenv
python3 -m venv venv

# Active Virtualenv
source venv/bin/activate

# You should now be inside the Virtual Environment
$ (venv) 
```

#### Install Dependencies
```shell
pip install -r requirements.txt

# This will install the following:
- cython
- pyside6
- setuptools
- xmltodict
```
### Execution

```shell
# Go to CDI Grading Tool Directory
cd cdi-grading-tool-alpha;

# Launch GUI
python3 main.py;

# Launch Console Only
python3 main.py --console-only;
```

<!-- ROADMAP -->
## Roadmap

- [ ] Add full change logs.
- [ ] Add "--console-only" argument.

See the [open issues](https://github.com/othneildrew/Best-README-Template/issues) for a full list of proposed features (and known issues).

<!-- LICENSE -->
## License
Distributed under the MIT License. See `LICENSE.txt` for more information.

<!-- CONTACT -->
## Contact

Nick Hayhurst - Interact/Cedar - nick.hayhurst@interactdc.com

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* TODO...
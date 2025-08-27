<h1 align='center' style="text-align:center; font-weight:bold; font-size:2.0em;letter-spacing:2.0px;"> Enhancing Search Privacy on Tor: Advanced Deep Keyword Fingerprinting Attacks and BurstGuard Defense </h1>

<p align='center' style="text-align:center; font-weight:bold; font-size:2.0em;letter-spacing:2.0px;"> <b> Chai Won Hwang*,  Hae Seung Jeon*, Ji Woo Hong, Ho Sung Kang, Nate Mathews, Goun Kim, and Se Eun Oh† </b> </p>

<p align='center' style="text-align:center; font-size:2.0em;letter-spacing:2.0px;"> *Equally credited authors. †Corresponding author. </p>


> [!NOTE]
> This is the **Keyword Fingerprinting Crawler** used in *Enhancing Search Privacy on Tor: Advanced Deep Keyword Fingerprinting Attacks and BurstGuard Defense* work, presented in the ASIACCS'25.


## 1. Environment

For KF-Crawler, we used Ubuntu 20.04 LTS VM on a Windows 10 desktop, installed using Oracle VirtualBox. We recommend having a minimum of 64GB of storage and 2048 MB of memory.


## 2. Prerequisites and Settings

### 2-1. Docker Installation

KF-Crawler is run in the Docker environment, which can be installed by:

```bash
$ sudo apt-get update
$ sudo apt-get install docker.io
$ sudo systemctl start docker
$ sudo systemctl enable docker
```

### 2-2. Network Setting

Check device number using the `ifconfig` command, and update the `DEVICE` variable with your device number in the `Makefile`.

```bash
$ ifconfig
```

## 3. Keywords

For our work, we utilized the [Keyword Tool website](https://keywordtool.io/) to extract the top 273 frequently searched keywords as monitored keywords. However, you can change the `top_273.txt` file for any keywords you want to visit.

## 4. Contacts
Please contact us if you have any questions about KF-Crawler.

- Chai Won Hwang, ifetayo@ewhain.net
- Haeseung Jeon, haeseungjeon@ewha.ac.kr
- Se Eun Oh, seoh@ewha.ac.kr

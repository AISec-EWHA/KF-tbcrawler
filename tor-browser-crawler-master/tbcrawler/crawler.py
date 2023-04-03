import sys
import pyshark
import subprocess
from os.path import join, split, getsize
from os import remove
from pprint import pformat
from time import sleep, time

from selenium.common.exceptions import TimeoutException, WebDriverException, ElementNotVisibleException, \
    NoSuchElementException
from selenium.webdriver.common.by import By

import tbcrawler.common as cm
import tbcrawler.utils as ut
from tbcrawler.dumputils import Sniffer
from tbcrawler.log import wl_log

import random
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# added action chains for clicking element
from bs4 import BeautifulSoup

import zipfile
import os
from pathlib import Path
import shutil


class Crawler(object):
    def __init__(self, driver, controller, screenshots=True, device="eth0"):
        self.driver = driver
        self.controller = controller
        self.screenshots = screenshots
        self.device = device
        self.job = None

    def crawl(self, job):
        """Crawls a set of urls in batches."""
        self.job = job
        wl_log.info("Starting new crawl")
        wl_log.info(pformat(self.job))
        for self.job.batch in range(self.job.batches):
            wl_log.info("**** Starting batch %s ***" % self.job.batch)
            self.controller.restart_tor()
            self._do_batch()
            sleep(float(self.job.config['pause_between_batches']))


    def post_visit(self):
        guard_ips = set([ip for ip in self.controller.get_all_guard_ips()])
        wl_log.debug("Found %s guards in the consensus.", len(guard_ips))
        wl_log.info("Filtering packets without a guard IP.")
        try:
            ut.filter_pcap(self.job.pcap_file, guard_ips)
        except Exception as e:
            wl_log.error("ERROR: filtering pcap file: %s.", e)
            wl_log.error("Check pcap: %s", self.job.pcap_file)

    def _do_batch(self):
        """
        Must init/restart the Tor process to have a different circuit.
        If the controller is configured to not pollute the profile, each
        restart forces to switch the entry guard.
        """
        # with self.controller.launch():
        for self.job.site in range(len(self.job.urls)):
            if len(self.job.url) > cm.MAX_FNAME_LENGTH:
                wl_log.warning("URL is too long: %s" % self.job.url)
                continue
            self._do_instance()
            sleep(float(self.job.config['pause_between_videos']))

    def _do_instance(self):
        for self.job.visit in range(self.job.visits):
            ut.create_dir(self.job.path)
            wl_log.info("*** Visit #%s to %s ***", self.job.visit, self.job.url)
            # self.job.screen_num = 0
            with self.driver.launch():
                try:
                    self.driver.set_page_load_timeout(cm.SOFT_VISIT_TIMEOUT)
                except WebDriverException as seto_exc:
                    wl_log.error("Setting soft timeout %s", seto_exc)
                self._do_restart()
            sleep(float(self.job.config['pause_between_loads']))
            self.post_visit()
            self.do_analysis()
            self.send_server()

    ##################################################################################
    def send_server(self):
        """file size check"""
        folder_size = 0
        file_path = cm.CRAWL_DIR
        owd = os.getcwd()
        os.chdir(file_path)
        for (path, dir, files) in os.walk(file_path):
            for file in files:
                file_size = getsize(os.path.join(os.path.join(path, file)))
                #wl_log.info(file + " " + str(file_size))
                folder_size += file_size

        wl_log.info(cm.CRAWL_DIR)
        wl_log.info(folder_size)
        os.chdir(owd)
        limit_size = 25*1024*1024*1024      #byte
        if folder_size >= limit_size:
            """
            make zip file and send it to server
            1. zip all files in result folder
            2. send it to server
            3. delete result folder
            """

            """ make zip file """
            file_path = cm.CRAWL_DIR  # RESULTS_DIR = join(BASE_DIR, 'results')
            owd = os.getcwd()
            os.chdir(file_path)
            zip_file = zipfile.ZipFile(join(file_path, "zipfile" + str(self.job.stampNum) + ".zip"), "w")
            for (path, dir, files) in os.walk(file_path):
                for file in files:
                    if ("html_" in file) or ("txt_" in file):
                        zip_file.write(os.path.join(os.path.relpath(path, file_path), file), compress_type=zipfile.ZIP_DEFLATED)
            """for path in Path(file_path).rglob("*"):
                zip_file.write(path, compress_type = zipfile.ZIP_DEFLATED)"""
            zip_file.close()
            sleep(1)

            """ send zip file to server """
            _id = ""           #server ID
            password = ""       #server password
            zfile = os.path.join(file_path, "zipfile" + str(self.job.stampNum) + ".zip")
            self.job.stampNum += 1
            wl_log.info(f'sshpass -p "{password}" scp {zfile} {_id}:/data/KF/dataset/result/vm')
            cmd = f'sshpass -p "{password}" scp -o StrictHostKeyChecking=no {zfile} {_id}:/data/KF/dataset/result/vm'
            zresult = subprocess.run(cmd, shell=True, text=True, check=True)
            wl_log.info(zresult.returncode)
            # os.system(f'sshpass -p "{password}" scp {zfile} {_id}:/data/KF/dataset/result')
            # sleep(5)
            # scp_process = subprocess.Popen(cmd, shell=True, text=True)
            # scp_process.wait()
            # wl_log.info(zresult.returncode)
            # os.system(f'sshpass -p "{password}" scp {zfile} {_id}:/data/KF/dataset/result') 

            """ remove results 
            for files in os.listdir(file_path):
                path = os.path.join(file_path, files)
                if "logs" not in str(path):
                    try:
                        shutil.rmtree(path)
                    except OSError:
                        os.remove(path)
            os.chdir(owd) """

    ##################################################################################
    def do_analysis(self):
        # analyze pcap file
        with open(self.job.output_file(self.job.batch, self.job.site, self.job.batch * self.job.visits + self.job.visit),
                  'w') as outfile:
            capture = pyshark.FileCapture(self.job.pcap_file)
            conversations = []
            for packet in capture:
                timestamp = float(packet.frame_info.time_relative)  # delta time
                direction = " "
                source_address = packet.ip.src
                if "10.0." not in source_address:  # 10.0 부분은 vm마다 다를 수 있으므로, 확인 필요
                    direction = '-'
                length = int(packet.tcp.len)
                if length >= 512:
                    conversations.append("{:.2f}\t{}{}\n".format(timestamp, direction, length))
            outfile.write(''.join(conversations))
            #if len(outfile.readlines()) < 100:

    ##################################################################################
    def _do_restart(self):
        """
        Must restart Tor process and revisit keyword if there is CAPTCHA
        """
        if self._do_visit() is True:
            wl_log.warning("*** restarting Tor process ***")
            self.controller.restart_tor()
            wl_log.warning("restarted Tor process")
            self._do_restart()

    ##################################################################################

    def _do_visit(self):
        with Sniffer(path=self.job.pcap_file, filter=cm.DEFAULT_FILTER,
                     device=self.device, dumpcap_log=self.job.pcap_log):
            sleep(1)  # make sure dumpcap is running

            isCaptcha = False
            if not isCaptcha:
                try:
                    screenshot_count = 0
                    with ut.timeout(cm.HARD_VISIT_TIMEOUT):

                        ##################################################################################
                        # type keyword character by character
                        # self.driver.get('http://www.google.com') #google
                        self.driver.get('http://www.bing.com')  # bing
                        # self.driver.get('http://www.duckduckgo.com') #duckduckgo

                        wait = WebDriverWait(self.driver, 3)
                        sleep(5)  # do not change - wait until web page is loaded

                        try:
                            """
                            try: #google: check if there is cookie pop-up
                                self.driver.implicitly_wait(0) # do not change - avoid collision with WebDriverWait
                                wl_log.info("check if there is cookie pop-up")
                                cookie = WebDriverWait(self.driver,3).until(EC.presence_of_element_located((By.ID, 'L2AGLb')))
                                if cookie.is_displayed():
                                    wl_log.info("cookie pop-up exists, click 'Accept all' button")
                                    cookie.click()
                            except Exception as exc:
                                wl_log.error("Exception: cookie pop-up do not exists")
                                pass
                            """

                            search = wait.until(EC.element_to_be_clickable((By.NAME, "q")))

                            a = self.job.url
                            for c in list(a):
                                search.send_keys(c)
                                sleep(random.uniform(0.7, 1.5))
                            sleep(1)
                            search.send_keys(Keys.ENTER)
                            sleep(10)  # bing, duckduckgo

                        except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                            print("Exception!")
                            isCaptcha = True
                            return isCaptcha
                        ##################################################################################
                        # check html file size
                        html_source = self.driver.page_source
                        html_source = html_source.encode('utf-8').decode('ascii', 'ignore')
                        soup = BeautifulSoup(html_source, "lxml")

                        with open(self.job.html_file(self.job.batch, self.job.site, self.job.batch * self.job.visits + self.job.visit), 'w') as f_html:
                            f_html.write(soup.prettify())
                        b = getsize(self.job.html_file(self.job.batch, self.job.site, self.job.batch * self.job.visits + self.job.visit))
                        print("out_png size->" + str(b))
                        if b <= 270000:  # smaller than 270kb
                            print("No Result!")
                            isCaptcha = True
                            return isCaptcha
                        ##################################################################################
                        # take first screenshot
                        sleep(2)
                        if self.screenshots:
                            try:
                                self.driver.get_screenshot_as_file(self.job.png_file(screenshot_count))
                                screenshot_count += 1
                            except WebDriverException:
                                wl_log.error("Cannot get screenshot.")
                                isCaptcha = True
                                return isCaptcha
                        ##################################################################################
                except (cm.HardTimeoutException, TimeoutException):
                    wl_log.error("Visit to %s reached hard timeout!", self.job.url)
                    isCaptcha = True
                    return isCaptcha
                except Exception as exc:
                    wl_log.error("Unknown exception: %s", exc)
                    isCaptcha = True
                    return isCaptcha
            else:
                isCaptcha = True
                wl_log.error("CAPTCHA!")
        return isCaptcha


class CrawlJob(object):
    def __init__(self, config, urls):
        self.urls = urls
        self.visits = int(config['visits'])
        self.batches = int(config['batches'])
        self.config = config

        # state
        self.site = 0
        self.visit = 0
        self.batch = 0

        self.stampNum = 0

    @property
    def pcap_file(self):
        return join(self.path, "capture.pcap")

    @property
    def pcap_log(self):
        return join(self.path, "dump.log")

    @property
    def instance(self):
        return self.batch * self.visits + self.visit

    @property
    def url(self):
        return self.urls[self.site]

    @property
    def path(self):
        attributes = [self.batch, self.site, self.instance]
        return join(cm.CRAWL_DIR, "_".join(map(str, attributes)))

    def png_file(self, time):
        return join(self.path, "screenshot_{}.png".format(time))

    #########################################################################################
    def html_file(self, batchIndex, keywordIndex, instanceIndex):
        return join(self.path, "html_{}-{}-{}.html".format(batchIndex, keywordIndex, instanceIndex))

    def output_file(self, batchIndex, keywordIndex, instanceIndex):
        return join(self.path, "txt_{}-{}-{}.txt".format(batchIndex, keywordIndex, instanceIndex))

    ########################################################################################

    def __repr__(self):
        return "Batches: %s, Sites: %s, Visits: %s" \
            % (self.batches, len(self.urls), self.visits)

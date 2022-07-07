import pickle
import os
import time
import pandas as pd
import re
import requests
from lxml import html
from dataclasses import dataclass, field
from .top_level_domains import TOP_LEVEL_DOMAINS

@dataclass
class Info:
    url:str
    emails:set()= field(default_factory=set)

class ExtractEmails:
    """
    Extract emails from a given website
    """

    def __init__(self, url: str, depth: int=None, print_log: bool=False, ssl_verify: bool=True, user_agent: str=None, request_delay: float=0):
        self.delay = request_delay
        self.verify = ssl_verify
        self.url=self.format_url(url)
        self.print_log = print_log
        self.depth = depth
        self.scanned = []
        self.for_scan = []
        self.infos=[]
        self.emails = []
        self.headers = {'User-Agent': user_agent}
        self.extract_emails(self.url)

    def format_url(self, url):
        formated_url=url
        if url.endswith('/'): formated_url = url[:-1]
        if "https://" not in formated_url: formated_url="https://"+formated_url
        return formated_url


    def extract_emails(self, url:str):
        r = requests.get(url, headers=self.headers, verify=self.verify)
        self.scanned.append(url)
        if r.status_code == 200:
            self.get_all_links(r.content)
            self.get_emails(url, r.text)
        for new_url in self.for_scan[:self.depth]:
            if new_url not in self.scanned:
                time.sleep(self.delay)
                self.extract_emails(new_url)

    def print_logs(self, url, emails):
        print(f'URL: {url}, found emails: {len(emails)}')

    def is_bad_link(self, link_href):
        block_links=['news', 'archive', 'service', 'career', 'project', 'facebook', 'linkedin', 'reddit', 'twitter', 'amazon', 'uk.indeed.com', 'youtube', 'researchgate', 'sketchup', 'autodesk', '.edu']
        for blink in block_links:
            if blink in link_href.lower():
                return True
        return False

    def get_emails(self, url, page):
        emails = re.finditer(r'\b[\w.-]+?@\w+?\.(?!jpg|png|jpeg)(com|co.uk)\b', page)
        emails=[e.group(0) for e in emails]
        emails = [x.lower() for x in emails]
        emails = [x for x in emails if '.' + x.split('.')[-1] in TOP_LEVEL_DOMAINS]
        if emails:
            newemails=[]
            for email in emails:
                if email not in self.emails:
                    newemails.append(email)
            if newemails:
                self.emails.extend(newemails)
                self.infos.append(Info(url, set(newemails)))
        if self.print_log:
            self.print_logs(url, emails)

    def get_all_links(self, page):
        try:
            tree = html.fromstring(page)
        except ValueError:
            tree = None
        if tree is not None:
            all_links = tree.findall('.//a')
            for link in all_links:
                try:
                    link_href = link.attrib['href']
                    if link_href.startswith(self.url) or link_href.startswith('/'):
                        if link_href.startswith('/'):
                            link_href = self.url + link_href
                        if link_href not in self.for_scan and not self.is_bad_link(link_href):
                            self.for_scan.append(link_href)
                except KeyError:
                    pass

    def to_csv(self, filename):
        result=[]
        visited_emails=[]
        for info in self.infos:
            for email in info.emails:
                if email not in visited_emails:
                    result.append({'page':info.url, 'email':email})
                    visited_emails.append(email)
        if result:
            df=pd.DataFrame.from_dict(result)
            df.to_csv(filename)
            print(f'Created {filename}')
        

if __name__ == '__main__':
    em = ExtractEmails('https://www.point2.co.uk', 
                        print_log=True, 
                        user_agent='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0',
                        depth=1000)
    em.to_csv('point2.csv')
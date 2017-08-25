#!/usr/bin/env python

__all__ = ['doi_to_wos', 'query', 'single', 'doi_to_wos_full', 'multi_doi']

from xml.etree import ElementTree as _ET
from xml.dom import minidom as _minidom
import re as _re
from multiprocessing.dummy import Pool as ThreadPool
import itertools
import time
import logging
logger = logging.getLogger(__name__)

record_limit = 100
speed_limit = 10 # Requests per n seconds
delay = 1 # in n seconds (throttle limit)
pool = ThreadPool(speed_limit) 

def single(wosclient, wos_query, xml_query=None, count=5, offset=1):
    """Perform a single Web of Science query and then XML query the results."""
    logger.debug('Query: {}'.format(wos_query))
    result = wosclient.search(wos_query, count, offset)
    xml = _re.sub(' xmlns="[^"]+"', '', result.records, count=1).encode('utf-8')
    if xml_query:
        xml = _ET.fromstring(xml)
        return [el.text for el in xml.findall(xml_query)]
    else:
        return _minidom.parseString(xml).toprettyxml()


def query(wosclient, wos_query, xml_query=None, count=5, offset=1, limit=100):
    """Query Web of Science and XML query results with multiple requests."""
    results = [single(wosclient, wos_query, xml_query, min(limit, count-x+1), x)
               for x in range(offset, count+1, limit)]
    if xml_query:
        return [el for res in results for el in res]
    else:
        pattern = _re.compile(r'.*?<records>|</records>.*', _re.DOTALL)
        return ('<?xml version="1.0" ?>\n<records>' +
                '\n'.join(pattern.sub('', res) for res in results) +
                '</records>')


def doi_to_wos(wosclient, doi):
    """Convert DOI to WOS identifier."""
    results = query(wosclient, 'DO="{}"'.format(doi) , './REC/UID', count=1)
    time.sleep(delay)
    if results:
        return  ('{},{}'.format(doi, results[0].lstrip('WOS:')))
    else:
        return ('{},'.format(doi))


def doi_to_wos_full(wosclient, query):
    """Handle queries from multi_doi."""
    results = single(wosclient, query , None, count=record_limit)
    time.sleep(delay)
    print(results)



def multi_doi(wosclient, doifile, onlyid):
    """Query many DOIs in a CSV file."""
    with open(doifile, 'r') as f:
        doi_list = f.readline().strip().split(',')

        if onlyid:
            logger.info('Retrieving WOS IDs for {} DOIs, please '
                        'wait...'.format(len(doi_list)))
            results = pool.starmap(doi_to_wos,
                                   zip(itertools.repeat(wosclient), doi_list)) 
            if results:
                print('doi,wos id')
                for line in results:
                    print(line) if line else None
        else:
            logger.info('Querying WOS for {} DOIs, please '
                        'wait...'.format(len(doi_list))) 
            i=0
            queries=[]
            while i < len(doi_list): 
                # Chunk into combined DOI queries equivalent to the
                # max records returned
                chunk = doi_list[i:i+record_limit]
                chunk = 'DO=(' + ' OR '.join(chunk) + ')'
                queries.append(chunk)
                i+=record_limit

            results = pool.starmap(doi_to_wos_full,
                                   zip(itertools.repeat(wosclient), queries))
            



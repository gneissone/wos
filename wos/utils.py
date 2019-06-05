#!/usr/bin/env python

__all__ = ['doi_to_wos', 'query', 'single', 'doi_to_wos_full', 'multi_doi']

from xml.etree import ElementTree as _ET
from xml.dom import minidom as _minidom
import re as _re
from multiprocessing.dummy import Pool as ThreadPool
import itertools
import time
import logging
import re
logger = logging.getLogger(__name__)

record_limit = 100
speed_limit = 1 # Requests per n seconds
delay = 1 # in n seconds (throttle limit)
pool = ThreadPool(speed_limit)

_illegal_xml_chars_RE = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')

def escape_xml_illegal_chars(val, replacement='?'):
    """Filter out characters that are illegal in XML.

    Looks for any character in val that is not allowed in XML
    and replaces it with replacement ('?' by default).
    """
    return _illegal_xml_chars_RE.sub(replacement, val)

def single(wosclient, wos_query, xml_query=None, count=5, offset=1):
    """Perform a single Web of Science query and then XML query the results."""
    logger.info('Query: {}'.format(wos_query))
    result = wosclient.search(wos_query, count, offset)
    xml = _re.sub(' xmlns="[^"]+"', '', result.records, count=1).encode('utf-8')
    if xml_query:
        xml = _ET.fromstring(xml)
        return [el.text for el in xml.findall(xml_query)]
    else:
        return _minidom.parseString(xml).toprettyxml()


def single_xmlout(wosclient, wos_query, xml_query=None, count=5, offset=1):
    """Perform a single Web of Science query and then XML query the results."""
    logger.info('Query: {}'.format(wos_query))
    result = wosclient.search(wos_query, count, offset)
    recordsFound = result.recordsFound
    queryId = result.queryId
    logger.info("Records found: {}".format(recordsFound))


    while offset < recordsFound:
        logger.info("Offset: {} QueryID: {}".format(offset, queryId))

        xml = _re.sub(' xmlns="[^"]+"', '', result.records, count=1).encode('utf-8')
        #logger.info('XML QUERY:{}'.format(xml_query))
        if xml_query:
            xml = _ET.fromstring(xml)


            for res in xml.findall(xml_query):
                uid = res.find('UID').text[4:]
                eh = _ET.tostring(res, encoding='UTF-8', method='xml')
                #eh = escape_xml_illegal_chars(eh)
                #logger.info('Eh after escape: {}'.format(eh))
                try:
                    eh = _minidom.parseString(eh).toprettyxml()
                    with open(uid + ".xml", "w") as f:
                        f.write(eh)
                except:
                    logger.error('Error processing document with UID {}, saving un-pretty result'.format(uid))
                    with open(uid + ".xml", "wb") as f:
                        f.write(eh)

            #return [_ET.tostring(el, encoding='utf8', method='xml') for el in xml.findall(xml_query)]
        else:
            return _minidom.parseString(xml).toprettyxml(encoding="UTF-8")

        offset += record_limit
        result = wosclient.retrieve(queryId, count, offset)


def query(wosclient, wos_query, xml_query=None, count=5, offset=1, limit=100):
    """Query Web of Science and XML query results with multiple requests."""
    results = [single(wosclient, wos_query, xml_query, min(limit, count-x+1), x)
               for x in range(offset, count+1, limit)]
    logger.info('Offset: {}'.format(offset))
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
    logger.info(query)
    results = single_xmlout(wosclient, query , './REC', count=record_limit)
    time.sleep(delay)



def multi_doi(wosclient, doifile, onlyid, ut_mode=False):
    """Query many DOIs in a CSV file and save as single XML files."""
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
                if ut_mode:
                    chunk = 'UT=(' + ' OR '.join(chunk) + ')'
                else:
                    chunk = 'DO=(' + ' OR '.join(chunk) + ')'
                queries.append(chunk)
                i+=record_limit

            results = pool.starmap(doi_to_wos_full,
                                   zip(itertools.repeat(wosclient), queries))

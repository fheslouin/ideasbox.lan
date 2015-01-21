import csv
import json
import os
import urllib2

from django.core.files.base import ContentFile
from django.utils.translation import ugettext as _

OPENLIBRARY_API_URL = 'https://openlibrary.org/api/books?'


def to_unicode(text):
    """Do its best to return an unicode string."""
    if isinstance(text, unicode):
        return text
    else:
        try:
            text = text.decode('utf-8')
        except UnicodeDecodeError:
            text = text.decode('latin-1')
        return text


def fetch_from_openlibrary(isbn):
    """Fetch notice from Open Library and return a ready to use dict.
    Doc: https://openlibrary.org/dev/docs/api/books."""
    args = {
        'jscmd': 'data',
        'format': 'json',
    }
    key = 'ISBN:{isbn}'.format(isbn=isbn)
    args['bibkeys'] = key
    args = '&'.join('{0}={1}'.format(k, v) for k, v in args.iteritems())
    url = '{base}{args}'.format(base=OPENLIBRARY_API_URL, args=args)
    content = read_url(url)
    try:
        data = json.loads(content).get(key)
    except ValueError:
        return
    if not data:
        return
    url = data.get('cover', {}).get('medium')
    if url:
        cover = load_cover_from_url(url)
    else:
        cover = None
    publishers = data.get('publishers', [])
    if publishers:
        publisher = publishers[0]['name']
    notice = {
        'isbn': isbn,
        'title': data.get('title'),
        'authors': ', '.join([a['name'] for a in data.get('authors', [])]),
        'cover': cover,
        'publisher': publisher
    }
    return notice


def read_url(url):
    try:
        response = urllib2.urlopen(url)
        return response.read()
    except:
        # Catch all, we don't want to fail in any way.
        return None


def load_cover_from_url(url):
    content = read_url(url)
    name = os.path.basename(url)
    if content and name:
        return ContentFile(content, name=name)


def load_from_moccam_csv(content):
    """Handle Moccam CSV import.
    See http://www.moccam-en-ligne.fr
    """
    FIELDS = [
        'isbn', 'title', 'authors', 'publisher', 'collection', 'year', 'price',
        'summary', 'small_cover', 'cover'
    ]
    content = content.split('\n')
    if not content or content[0].count('	') != 9:
        raise ValueError(_('Unable to parse file'))
    rows = csv.DictReader(content, fieldnames=FIELDS,
                          delimiter='	')
    for row in rows:
        if row['cover']:
            cover = load_cover_from_url(row['cover'])
        else:
            cover = None
        authors = row.get('authors', '')
        if ',' in authors:
            authors = authors.split(', ')
            authors.reverse()
            authors = ' '.join(authors)
        yield {
            'isbn': row['isbn'],
            # Moccam sucks in many ways, including encoding.
            'title': to_unicode(row['title']),
            'authors': to_unicode(authors),
            'publisher': to_unicode(row['publisher']),
            'summary': to_unicode(row['summary']),
            'cover': cover
        }

"""download documents from an IMAP account/server"""

import itertools
import click

import docdl
import docdl.util
import imaplib
import base64
import os
import email
import email.policy
import re
import unicodedata
import ast
import tempfile
import hashlib
from datetime import datetime

"""
blacklist a few words for filenames that you usually don't want
same for extensions

@todo make them configurable
"""
blacklist_filename = [ 'widerruf', 'bild', 'agb' ]
blacklist_extension = [ '.vcf' ]

def slugify(value, allow_unicode=True):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s\.-]', '', value.lower())
    value = re.sub(r'[-\s]+', '-', value)
    return value

def get_hash(file):
    if os.path.exists(file):
        BLOCK_SIZE = 65536
        file_hash = hashlib.sha256()
        with open(file, 'rb') as f:
            fb = f.read(BLOCK_SIZE)
            while len(fb) > 0:
                file_hash.update(fb)
                fb = f.read(BLOCK_SIZE)
    else:
        return None
    return file_hash.hexdigest()

def compare_hash(fileone, filetwo):
    hashone=get_hash(fileone)
    hashtwo=get_hash(filetwo)
    if hashone == hashtwo:
        return True
    return False

def getNewFileName(filename, counter=0):
    filepre, extension = os.path.splitext(filename)
    fileorg=filepre
    if counter > 0:
        file=f'{fileorg}_{counter}{extension}'
    else:
        file=f'{fileorg}{extension}'
    if os.path.exists(file):
        if counter > 1:
            i=1
            while i < counter:
                if compare_hash(file,f'{fileorg}_{i}{extension}'):
                    return False
                i+=1
        return getNewFileName(filename,counter + 1)
    else:
        return file

def parse_address(m):
    match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', m)
    return match.group(0)

def parse_issuer(m):
    #remove some common general names
    if 'Amazon Marketplace' in m:
        return slugify(re.search(r'^(.*) - Amazon Marketplace', m).group(1))
    if 'Amazon Payments' in m:
        return slugify(re.search(r'^(.*) - Amazon Payments', m).group(1))
    return slugify('.'.join(parse_address(m)[parse_address(m).index('@') + 1 :].split('.')[:-1]))

class Mutex(click.Option):
    # source: https://stackoverflow.com/questions/44247099/click-command-line-interfaces-make-options-required-if-other-optional-option-is by Stephen Rauch
    def __init__(self, *args, **kwargs):
        self.not_required_if:list = kwargs.pop("not_required_if")

        assert self.not_required_if, "'not_required_if' parameter required"
        kwargs["help"] = (kwargs.get("help", "") + "Option is mutually exclusive with " + ", ".join(self.not_required_if) + ".").strip()
        super(Mutex, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        current_opt:bool = self.name in opts
        for mutex_opt in self.not_required_if:
            if mutex_opt in opts:
                if current_opt:
                    raise click.UsageError("Illegal usage: '" + str(self.name) + "' is mutually exclusive with " + str(mutex_opt) + ".")
                else:
                    self.prompt = None
        return super(Mutex, self).handle_parse_result(ctx, opts, args)




class IMAP(docdl.WebPortal):
    """download documents from an IMAP account"""

    def __init__(self, login_id, password, useragent=None, arguments=None):
        # don't use headless user agent to avoid ing.de mistaking us for a bot
        super().__init__(
            login_id=login_id,
            password=password,
            arguments=arguments,
            useragent=None
        )
        self.mail = None
        if arguments['email_searchexp'] is None and (arguments['email_search'] is not None and arguments['email_field'] is not None):
            self.searchexp = '(' + arguments['email_field'] + ' ' + arguments['email_search'] + ')'
        else:
            self.searchexp = arguments['email_searchexp']
  


    def login(self):
        """authenticate"""
        try: 
            self.mail = imaplib.IMAP4_SSL(self.arguments['server'],self.arguments['port'])
            status, msg=self.mail.login(self.login_id, self.password)
            self.mail.select("inbox",readonly=True)
            return self.mail
        except imaplib.IMAP4.error as ex:
            print(ex)
            pass
        return False

    def logout(self):
        return self.mail.logout()


    def documents(self):
        """fetch list of documents"""
        #remove double spaces, since they are incompatible with the imap search terms
        searchstring = f'(X-GM-RAW has:attachment {self.searchexp})'.replace('  ', ' ').replace('( ','(').replace(' )',')')
        type, data = self.mail.search(None, None, searchstring)
        if type == 'OK':
            mail_ids=data[0].split()
        for num in mail_ids:
            type, data = self.mail.fetch(num, 'BODY.PEEK[]')
            mail = email.message_from_bytes(data[0][1], policy=email.policy.default)
            attachments=0
            for att in mail.iter_attachments():
                if any(word.lower() in att.get_filename().lower() for word in blacklist_filename):
                    continue
                if any(word.lower() in os.path.splitext(att.get_filename())[1].lower() for word in blacklist_extension):
                    continue
                attachments+=1
            if attachments > 0:
                i = 0
                if mail['Reply-To'] is None or parse_address(mail['Reply-To']) == parse_address(mail['From']):
                    issuer=parse_issuer(mail['From'])
                else:
                    issuer=parse_issuer(mail['Reply-To'])
                for att in mail.iter_attachments():
                    if any(word.lower() in att.get_filename().lower() for word in blacklist_filename):
                        continue
                    if any(word.lower() in os.path.splitext(att.get_filename())[1].lower() for word in blacklist_extension):
                        continue
                    filename=att.get_filename()
                    if attachments > 1:
                        filename, file_extension = os.path.splitext(att.get_filename())
                        filename=f"{filename}_{i+1}{file_extension}"
                    yield docdl.Document(
                       attributes={
                         'Message-ID': mail['Message-ID'],
                         'date': email.utils.parsedate_to_datetime(mail['Date']),
                         'issuer': issuer,
                         'filename': os.path.join(issuer,filename),
                         'aid':i
                       }
                    )
                    i+=1
            else:
                continue
        return []

    def documents_test(self):
        iter=None
        iter=self.search_documents(self.searchexp)
        for i, document in enumerate(iter):
            # set an id
            document.attributes['id'] = i
            # return document
            yield document

    def download(self, document):
        """download document"""
        # don't attempt download without url
        if "Message-ID" in document.attributes:
            if document.attributes['Message-ID'] is not None:
                filename = document.attributes['filename']
        filename = self.download_with_imaplib(document)
        return filename


    def download_with_imaplib(self, document):
        msgid = document.attributes['Message-ID']
        type, mails = self.mail.search(None, f'HEADER Message-ID {msgid}')
        partfiles={}
        for m in mails:
            type, data = self.mail.fetch(m, "(RFC822)")
            mail = email.message_from_bytes(data[0][1], policy=email.policy.default)
            aid=0
            for att in mail.iter_attachments():
                if aid == document.attributes['aid']:
                    filepre, extension = os.path.splitext(document.attributes['filename'])
                    path = os.path.dirname(document.attributes['filename'])
                    os.makedirs(path,exist_ok=True)
                    with tempfile.NamedTemporaryFile(suffix=extension, delete=False, dir=os.getcwd()) as f:
                        f.write(att.get_content())
                        epoch = int(document.attributes['date'].strftime('%s'))
                        os.utime(f.name, (epoch,epoch))
                        if compare_hash(document.attributes['filename'], f.name):
                            if os.path.exists(f.name):
                                os.remove(f.name)
                            return document.attributes['filename']
                        else:
                            i=0
                            filepreorg=filepre
                            filenamenew=getNewFileName(f'{filepre}{extension}',0)
                            if filenamenew is False:
                                os.remove(f.name)
                            else:
                                os.rename(f.name, filenamenew)
                        return f.name
                aid+=1
        return ''



@click.command()
@click.option(
    "-s",
    "--server",
    prompt=True,
    required=True,
    hide_input=False,
    envvar="DOCDL_IMAP_SERVER",
    show_envvar=True,
    help="IMAP Server"
)
@click.option(
    "-p",
    "--port",
    default=993,
    prompt=False,
    hide_input=False,
    envvar="DOCDL_IMAP_PORT",
    show_envvar=True,
    help="IMAP Port"
)
@click.option(
    "--email-field",
    prompt=False,
    hide_input=False,
    envvar="DOCDL_IMAP_SEARCHFIELD",
    show_envvar=True,
    help="IMAP search in email field",
    cls=Mutex,
    not_required_if=["email_searchtuple"]
)
@click.option(
    "--email-search",
    prompt=False,
    hide_input=False,
    envvar="DOCDL_IMAP_SEARCHTERM",
    show_envvar=True,
    help="IMAP Email search term",
    cls=Mutex,
    not_required_if=["email_searchtuple"]
)
@click.option(
    "--email-searchexp",
    default="[]",
    prompt=False,
    hide_input=False,
    envvar="DOCDL_IMAP_SEARCHEXP",
    show_envvar=True,
    help="IMAP Email search expression",
    cls=Mutex,
    not_required_if=["email_search","email_field"]
)

@click.pass_context
# pylint: disable=C0103
def imap(ctx, *args, **kwargs):
    """imap account (attachments)"""
    docdl.cli.run(ctx, IMAP)

from Cookie import SimpleCookie
from getpass import getpass
from hashlib import sha1
import os, re
from urlparse import urlparse, urljoin
from urllib import splituser, urlencode
from urllib2 import urlopen

from mercurial import httprepo
from mercurial import error
from mercurial import util

class CachingCookieHolder(dict):
    def __init__(self, path, prefix):
        self.path = path #PATH='/tmp'
        self.prefix = prefix #PREFIX='hg_form_'
        super(CachingCookieHolder, self).__init__()

    def _get_cookie_file(self, host):
        return os.path.join(self.path, self.prefix + sha1(host).hexdigest())

    def __getitem__(self, host):
        if host in self:
            return dict.__getitem__(self, host)
        else:
            cookiefile = self._get_cookie_file(host)
            if os.path.exists(cookiefile):
                inp =  open(cookiefile)
                cookie = inp.read()
                inp.close()
                dict.__setitem__(self, host, cookie)
                return cookie
        return None

    def __setitem__(self, host, value):
        cookiefile = self._get_cookie_file(host)
        out = open(cookiefile, 'w')
        out.write(value)
        out.flush()
        out.close()

def get_the_cookie(url, username=None, password=None):
    req = urlopen(url)
    data = req.read()
    hidden_inputs = re.findall('<INPUT.*HIDDEN.*NAME="(.*)".*VALUE="(.*)">', data)
    if username is None:
        username = raw_input('Username: ')
    if password is None:
        password = getpass()

    hidden_inputs.append(('username', username))
    hidden_inputs.append(('passcode', password))
    qs = urlencode(hidden_inputs)

    action = urljoin(url, re.findall('<FORM action="([^"]*)" .*>', data)[0])
    req2 = urlopen(action, data=qs)
    cookie = SimpleCookie(req2.info()['set-cookie'])
    return cookie.keys()[0] + "=" + cookie.values()[0].value

class formloginhttpsrepo(httprepo.httpsrepository):
    cookiejar = CachingCookieHolder('/tmp', 'hg_form_')

    def do_cmd(self, cmd, **args):
        username, host = splituser(urlparse(self.path).netloc)

        cookie = self.cookiejar[host]
        if cookie is not None:
            return super(formloginhttpsrepo, self).do_cmd(cmd, headers={'cookie' : cookie}, **args)
        else:
            try:
                return super(formloginhttpsrepo, self).do_cmd(cmd, **args)
            except error.RepoError, e:
                if 'does not appear to be an hg repository' in str(e):
                    cookie = get_the_cookie(self.path)
                    print 'Got cookie ' + cookie
                    self.cookiejar[host] = cookie
                    return super(formloginhttpsrepo, self).do_cmd(cmd, headers={'cookie' : cookie}, **args)
            else:
                raise e

def instance(ui, path, create):
    if path.startswith('https:'):
        return formloginhttpsrepo(ui, path)
    else:
        return httprepo.httprepository(ui, path)

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

COOKIE=None

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
    def do_cmd(self, cmd, **args):
        global COOKIE

        username, host = splituser(urlparse(self.path).netloc)
        cookiefile = os.path.join('/tmp', 'hgform_' + sha1(host).hexdigest())
        headers = {}

        if COOKIE is not None:
            return super(formloginhttpsrepo, self).do_cmd(cmd, headers={'cookie' : COOKIE}, **args)
        elif os.path.exists(cookiefile):
            inp =  open(cookiefile)
            COOKIE = inp.read()
            inp.close()
            return super(formloginhttpsrepo, self).do_cmd(cmd, headers={'cookie' : COOKIE}, **args)
        else:
            try:
                return super(formloginhttpsrepo, self).do_cmd(cmd, **args)
            except error.RepoError, e:
                if 'does not appear to be an hg repository' in str(e):
                    COOKIE = get_the_cookie(self.path)
                    print 'Got cookie ' + COOKIE
                    out = open(cookiefile, 'w')
                    out.write(COOKIE)
                    out.flush()
                    out.close()
                    return super(formloginhttpsrepo, self).do_cmd(cmd, headers={'cookie' : COOKIE}, **args)
            else:
                raise e

def instance(ui, path, create):
    if path.startswith('https:'):
        return formloginhttpsrepo(ui, path)
    else:
        return httprepo.httprepository(ui, path)

from mercurial import httprepo
from mercurial import hg
import formloginrepo

hg.schemes.update({'https' : formloginrepo})




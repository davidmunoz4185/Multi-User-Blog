import os
import re
import random
import hashlib
import hmac
from string import letters

import webapp2
import jinja2

import myHelper
from models import User
from models import Post

from google.appengine.ext import db

secret = 'secure_word'

def make_secure_val(val):
    """
        Creates secure value using secret.
    """
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    """
        Verifies secure value against secret.
    """
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

class BlogHandler(webapp2.RequestHandler):
    """
        This is a BlogHandler Class, inherits webapp2.RequestHandler,
        and provides helper methods.
    """
    def write(self, *a, **kw):
        """
            This method writes output to client browser.
        """
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        """
            This method renders html using template.
        """
        params['user'] = self.user
        return myHelper.jinja_render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        """
            Sets secure cookie to browser.
        """
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        """
            Reads secure cookie to browser.
        """
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        """
            Verifies user existance.
        """
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        """
            Removes login information from cookies.
        """
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        """
            This methods gets executed for each page and
            verfies user login status, using oookie information.
        """
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)

class MainPage(BlogHandler):
  def get(self):
      self.write('Hello, Udacity!')

def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)

class BlogFront(BlogHandler):
    def get(self):
        """
            This renders home page with all posts, sorted by date.
        """
        posts = Post.all().filter('parent_post =', None).order('-created')
        uid = self.read_secure_cookie('user_id')
        self.render('front.html', posts = posts, uid=uid)

class PostPage(BlogHandler):
    def get(self, post_id):
        """
            This renders home post page with content, comments and likes.
        """
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        uid = self.read_secure_cookie('user_id')

        if post.likes and uid in post.likes:
            likeText = 'unlike'
        else:
            likeText = 'like'

        totalLikes = len(post.likes)
        comments = Post.all().filter('parent_post =', post_id)

        if not post:
            self.error(404)
            return

        post._render_text = post.content.replace('\n', '<br>')
        self.render("post.html", post = post, likeText = likeText, totalLikes = totalLikes, uid = uid, comments = comments)

    def post(self, post_id):
        if not self.user:
            return self.redirect('/login')

        subject = self.request.get('subject')
        content = self.request.get('content')

        uid = self.read_secure_cookie('user_id')

        if subject and content:
            post = Post(parent = blog_key(), subject = subject, content = content, user_id = uid, parent_post = post_id)
            post.put()
            self.redirect('/post/%s' % post_id)
        else:
            error = "subject and content, please!"
            self.render("post.html", subject=subject, content=content, error=error)

class LikePage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        uid = self.read_secure_cookie('user_id')

        if not post:
            self.error(404)
            return

        if post.user_id != uid:

            if post.likes and uid in post.likes:
                post.likes.remove(uid)
            else:
                post.likes.append(uid)

            post.put()

            self.redirect('/post/%s' % str(post.key().id()))

        else:
            error = 'you can\'t like or unlike you own post'
            self.render("error.html", error = error)

class DeletePage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.redirect("/")
            return

        uid = self.read_secure_cookie('user_id')

        if post.user_id != uid:
            error = 'You don\'t have permission to delete this post'
        else:
            error = ''
            db.delete(key)

        self.render("delete.html", error = error)

class EditPage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return

        uid = self.read_secure_cookie('user_id')

        if post.user_id != uid:
            error = 'You don\'t have permission to edit this post'
        else:
            error = ''

        self.render("edit.html", post = post, error = error, uid=uid)

    def post(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return

        uid = self.read_secure_cookie('user_id')

        subject = self.request.get('subject')
        content = self.request.get('content')

        if subject and content and post.user_id == uid:
            post.subject = subject
            post.content = content
            post.put()
            if post.parent_post:
                redirect_id = post.parent_post
            else:
                redirect_id = post.key().id()
            self.redirect('/post/%s' % str(redirect_id))
        else:
            error = "subject and content, please!"
            self.render("edit.html", post = post, error=error)


class NewPost(BlogHandler):
    def get(self):
        uid = self.read_secure_cookie('user_id')
        if self.user:
            self.render("newpost.html",  uid=uid)
        else:
            return self.redirect("/login")

    def post(self):
        """
            Creates new post and redirect to new post page.
        """
        if not self.user:
            return self.redirect('/login')

        subject = self.request.get('subject')
        content = self.request.get('content')

        uid = self.read_secure_cookie('user_id')

        if subject and content:
            post = Post(parent = blog_key(), subject = subject, content = content, user_id = uid)
            post.put()
            self.redirect('/post/%s' % str(post.key().id()))
        else:
            error = "subject and content, please!"
            self.render("newpost.html", subject=subject, content=content, error=error)

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

class Signup(BlogHandler):
    def get(self):
        self.render("signup.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username = self.username,
                      email = self.email)

        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Register(Signup):
    def done(self):
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup.html', error_username = msg)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()

            self.login(u)
            self.redirect('/')

class Login(BlogHandler):
    def get(self):
        self.render('login.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/')
        else:
            msg = 'Invalid login'
            self.render('login.html', error = msg)

class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/')

class Welcome(BlogHandler):
    def get(self):
        if self.user:
            uid = self.read_secure_cookie('user_id')
            self.render('welcome.html', username = self.user.name, uid=uid)
        else:
            self.redirect('/signup')

app = webapp2.WSGIApplication([('/?', BlogFront),
                               ('/post/([0-9]+)', PostPage),
                               ('/delete/([0-9]+)', DeletePage),
                               ('/edit/([0-9]+)', EditPage),
                               ('/like/([0-9]+)', LikePage),
                               ('/newpost', NewPost),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/welcome', Welcome),
                               ],
                              debug=True)

from google.appengine.ext import db

class Post(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    ### New fields added ###
    user_id = db.StringProperty(required = True)
    ### List of uids who like Post ###
    likes = db.StringListProperty()

    ### For comments ###
    parent_post = db.StringProperty()

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return myHelper.jinja_render_str("post.html", p = self)
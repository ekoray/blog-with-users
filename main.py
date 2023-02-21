# import os
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, mapped_column
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar

# basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

gravatar = Gravatar(app, size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# CONNECT TO DB

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
#     os.path.join(basedir, 'blog.db')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


@ login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, int(user_id))


# CONFIGURE TABLES

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = mapped_column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")

    # This will act like a List of Comment objects attached to each User.
    # The "author" refers to the author property in the Comment class.
    comments = relationship("Comment", back_populates="author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id = mapped_column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = mapped_column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")

    # This will act like a List of Comment objects attached to each BlogPost.
    # The "blog_post" refers to the blog_post property in the Comment class.
    comments = relationship("Comment", back_populates="blog_post")

    # author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class Comment(db.Model):
    __tablename__ = "comments"

    id = mapped_column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), nullable=False)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = mapped_column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "comments" refers to the comments protperty in the User class.
    author = relationship("User", back_populates="comments")

    # Create Foreign Key, "blog_posts.id" the blog_posts refers to the tablename of BlogPost.
    blog_post_id = mapped_column(db.Integer, db.ForeignKey("blog_posts.id"))
    # Create reference to the BlogPost object, the "comments" refers to the comments protperty in the BlogPost class.
    blog_post = relationship("BlogPost", back_populates="comments")


with app.app_context():
    db.create_all()


def admin_only(f):
    @ wraps(f)
    def deco_func(*args, **kwargs):

        if current_user.get_id() != '1':
            return abort(403)

        return f(*args, **kwargs)

    return deco_func


@ app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts,  logged_in=current_user.is_authenticated, user_id=current_user.get_id())


@ app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():

        try:
            user = db.session.execute(db.select(User).filter_by(
                email=form.email.data)).scalar_one()
        except:
            user_email = form.email.data
            user_pass = generate_password_hash(
                form.password.data, "pbkdf2:sha256", salt_length=8)
            user_name = form.name.data

            new_user = User(
                name=user_name,
                email=user_email,
                password=user_pass
            )
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)
            return redirect(url_for('get_all_posts'))
        else:
            flash("You have already registered. Just log in.")
            return redirect(url_for('login'))

    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user_email = form.email.data
        user_password = form.password.data

        try:
            user = db.session.execute(
                db.select(User).filter_by(email=user_email)).scalar_one()
        except:
            flash("Wrong email. Please try again.")
            return redirect(url_for('login'))
        else:
            if check_password_hash(user.password, user_password):
                login_user(user)
                return redirect(url_for('get_all_posts'))

            flash("Wrong password. Please try again.")
            return redirect(url_for('login'))

    return render_template("login.html", form=form, logged_in=current_user.is_authenticated, user_id=current_user.get_id())


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    comment_form = CommentForm()
    requested_post = BlogPost.query.get(post_id)

    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text=comment_form.comment.data,
                author=current_user,
                blog_post=requested_post)

            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
        else:
            flash("Login to comment")
            return redirect(url_for('login'))

    return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated, user_id=current_user.get_id(), form=comment_form)


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)


@app.route("/new-post", methods=['GET', 'POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = post.author
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_edit=True, logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)

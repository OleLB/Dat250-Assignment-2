"""Provides all routes for the Social Insecurity application.

This file contains the routes for the application. It is imported by the social_insecurity package.
It also contains the SQL queries used for communicating with the database.
"""
import re
import base64
import os
from pathlib import Path

from flask import current_app as app

from flask import flash, redirect, render_template, send_from_directory, url_for, g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from social_insecurity import sqlite
from social_insecurity.forms import CommentsForm, FriendsForm, IndexForm, PostForm, ProfileForm
from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import login_user, UserMixin, login_required, current_user, LoginManager

login_manager = LoginManager()
login_manager.init_app(app)

limiter = Limiter(get_remote_address, app=app, default_limits=["1000 per day"])

# Define the User model
class User(UserMixin):          #! This needs to be updated with eveything we need to do with the user data
    def __init__(self, id, username):
        self.id = id
        self.username = username

    @staticmethod
    def get(user_id):
        # Replace this with your own logic to retrieve a user from the database by ID
        # For example:
        # user = User.query.get(user_id)
        return User(user_id, "example_username")  # Temporary example; replace with actual user lookup



# Register the user_loader function with the login_manager
@login_manager.user_loader
def load_user(user_id):
    get_user = f"""
             SELECT *
             FROM Users
             WHERE id = '{user_id}';
             """
    db_user = sqlite.query(get_user, one=True)
    if db_user:
        return User(id=db_user["id"], username=db_user["username"])
    return None



def verify_username(username):
    # input validation, only allow alphanumeric characters
    pattern = r'[^a-zA-Z0-9_]' # only allow alphanumeric characters and underscore
    if bool(re.search(pattern, username)):
        return False
    
    # Check if the user exists
    get_user = f"""
        SELECT *
        FROM Users
        WHERE username = '{username}';
        """
    user = sqlite.query(get_user, one=True)
    if user is None:
        return False
    
    return True


def xss_and_sqli_cehck(input):
    # content check, sanitize to prevent XSS and SQLI
    patter = r'[^a-zA-Z0-9\s\.\,\!\?\:\-]' # only allow alphanumeric, whitespace, . , ! ? : -
    if bool(re.search(patter, input)):
        return False
    return True

def generate_nonce():
    return base64.b64encode(os.urandom(16)).decode('utf-8')

# csp rules (Content Security Policy)
@app.after_request
def set_csp(response):
    # if g.nonce does not exist, create it
    if not hasattr(g, 'nonce'):
        g.nonce = generate_nonce()

    csp = (
        "default-src 'self' https://maxcdn.bootstrapcdn.com;"
        f"script-src https://cdn.jsdelivr.net 'nonce-{g.nonce}';"
        "style-src 'self' https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css 'unsafe-inline';"
        "frame-ancestors 'none';"
        "form-action 'self';"
    )

    response.headers['Content-Security-Policy'] = csp
    return response


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
@limiter.limit(limit_value="10/minute")
def index():
    """Provides the index page for the application.

    It reads the composite IndexForm and based on which form was submitted,
    it either logs the user in or registers a new user.

    If no form was submitted, it simply renders the index page.
    """
    index_form = IndexForm()
    login_form = index_form.login
    register_form = index_form.register    

    if login_form.is_submitted() and login_form.submit.data:
        
        # input validation for login
        username_input = login_form.username.data
        if not username_input.isalnum():   # Method to check if alphanumberical, to prevent SQLI
            flash("Only alphanumeric characters are allowed", category="warning")
            return render_template("index.html.j2", title="Welcome", form=index_form)
        
        get_user = f"""
             SELECT *
             FROM Users
             WHERE username = '{login_form.username.data}';
             """
        db_user = sqlite.query(get_user, one=True)

        if db_user is None: # Check that user exists, before checking password
            flash("Wrong password or username", "warning")
            return render_template("index.html.j2", title="Welcome", form=index_form)
        

        if check_password_hash(db_user["password"], login_form.password.data):
            UserObject = User(db_user["id"], db_user["username"])   # Create a User object
            login_user(UserObject) # Log in the user
            return redirect(url_for("stream", username=db_user["username"])) # Redirect to the stream page
        else:
            flash("Wrong password or username", "warning")


    elif register_form.is_submitted() and register_form.submit.data:
        
        reg_username = register_form.username.data
        reg_first_name = register_form.first_name.data
        reg_last_name = register_form.last_name.data
        reg_password = register_form.password.data
        confirm_password_input = register_form.confirm_password.data

        # Password requirements
        if len(reg_password) < 8:
            flash("Password must be at least 8 characters long", category="warning")
            return render_template("index.html.j2", title="Welcome", form=index_form)
        
        if not any(char.isdigit() for char in reg_password):
            flash("Password must contain at least one digit", category="warning")
            return render_template("index.html.j2", title="Welcome", form=index_form)
        
        if not any(char.islower() for char in reg_password):
            flash("Password must contain at least one lowercase letter", category="warning")
            return render_template("index.html.j2", title="Welcome", form=index_form)
        
        if not any(char.isupper() for char in reg_password):
            flash("Password must contain at least one uppercase letter", category="warning")
            return render_template("index.html.j2", title="Welcome", form=index_form)
        
        if not any(char in "@!#$%^&+=" for char in reg_password):
            flash("Password must contain at least one special character (@!#$%^&+=)", category="warning")
            return render_template("index.html.j2", title="Welcome", form=index_form)

        # input validation for registration
        bad_password_chars = ["'", '"', ";", "--", "/*", "*/"] # to prevent SQLI
        for char in bad_password_chars:
            if char in reg_password:
                flash("Invalid password", category="warning")
                return render_template("index.html.j2", title="Welcome", form=index_form)
        
        # make sure passwords match
        if confirm_password_input != reg_password:
            flash("Passwords do not match", category="warning")
            return render_template("index.html.j2", title="Welcome", form=index_form)
        
        # only allow alphanumeric characters for username, first name and last name
        if not reg_username.isalnum() or not reg_first_name.isalnum() or not reg_last_name.isalnum():   # Method to check if alphanumberical, to prevent SQLI
            flash("Only alphanumeric characters are allowed", category="warning")
            return render_template("index.html.j2", title="Welcome", form=index_form)
        
        # check if username already exists
        check_username = f"""
             SELECT *
             FROM Users
             WHERE username = '{reg_username}';
             """
        user = sqlite.query(check_username, one=True)
        if user is not None:
            flash("Username not available", category="warning")
            return render_template("index.html.j2", title="Welcome", form=index_form)

        password_hash = generate_password_hash(reg_password)

        insert_user = f"""
            INSERT INTO Users (username, first_name, last_name, password)
            VALUES ('{register_form.username.data}', '{register_form.first_name.data}', '{register_form.last_name.data}', '{password_hash}');
            """
        sqlite.query(insert_user)
        flash("User successfully created!", category="success")
        return redirect(url_for("index"))

    return render_template("index.html.j2", title="Welcome", form=index_form)

@app.route("/stream/<string:username>", methods=["GET", "POST"])
@login_required
def stream(username: str):
    """Provides the stream page for the application.

    If a form was submitted, it reads the form data and inserts a new post into the database.

    Otherwise, it reads the username from the URL and displays all posts from the user and their friends.
    """

    if current_user.username != username:
        return render_template("index.html.j2", title="Welcome", form=IndexForm())

    #print("current user: ", current_user.username)
    # if current_user.username != username:
    #     return render_template("index.html.j2", title="Welcome", form=IndexForm())
    
    # Check if the username is alphanumerical and exists
    if not verify_username(username):
        return render_template("index.html.j2", title="Welcome", form=IndexForm())

    post_form = PostForm()
    get_user = f"""
        SELECT *
        FROM Users
        WHERE username = '{username}';
        """
    user = sqlite.query(get_user, one=True)

    # following variables is used later in another if, keep outside
    valid_check = ["jpg","jpeg","gif","png"]
    pattern = r'[^a-zA-Z0-9]'  # patten will return true if there are any special characters
    if post_form.is_submitted():
        if not post_form.image.data and not post_form.content.data.strip():
            #utelukker tomme posts
            flash("Invalid post content! please check your img/text if valid", category="warning")
            return redirect(url_for("stream", username=username))
        elif post_form.image.data:
            img_check = str(post_form.image.data.filename).split(".")
            if img_check[-1].lower() not in valid_check or len(img_check) != 2 or bool(re.search(pattern, img_check[0])):
                #bildet er ikke ok
                flash("Invalid file, please restrain from using special characters, and only use .jpg, .jpeg, .png or .gif", category="warning")
                return redirect(url_for("stream", username=username))
        
        # checks for xss
        if not xss_and_sqli_cehck(post_form.content.data): 
            flash("Invalid text, please use valid characters", category="warning")
            return redirect(url_for("stream", username=username))

        #posts the content
        if post_form.image.data:
            path = Path(app.instance_path) / app.config["UPLOADS_FOLDER_PATH"] / post_form.image.data.filename
            post_form.image.data.save(path)
        insert_post = f"""
        INSERT INTO Posts (u_id, content, image, creation_time)
        VALUES ({user["id"]}, '{post_form.content.data}', '{post_form.image.data.filename}', CURRENT_TIMESTAMP);
        """
        sqlite.query(insert_post)
        return redirect(url_for("stream", username=username))
    
    get_posts = f"""
         SELECT p.*, u.*, (SELECT COUNT(*) FROM Comments WHERE p_id = p.id) AS cc
         FROM Posts AS p JOIN Users AS u ON u.id = p.u_id
         WHERE p.u_id IN (SELECT u_id FROM Friends WHERE f_id = {user["id"]}) OR p.u_id IN (SELECT f_id FROM Friends WHERE u_id = {user["id"]}) OR p.u_id = {user["id"]}
         ORDER BY p.creation_time DESC;
        """
    # TODO: legg til at hvis det finnes noe i db som ikke følger valid_check, så blir det ikke rendered, evt slettet
    posts = sqlite.query(get_posts)
    for post in posts:
        if post[3]:
            name = post[3].split(".")
            if len(name) != 2 or name[-1].lower() not in valid_check:
                posts.remove(post)
    return render_template("stream.html.j2", title="Stream", username=username, form=post_form, posts=posts)


@app.route("/comments/<string:username>/<int:post_id>", methods=["GET", "POST"])
@login_required
def comments(username: str, post_id: int):
    """Provides the comments page for the application.

    If a form was submitted, it reads the form data and inserts a new comment into the database.

    Otherwise, it reads the username and post id from the URL and displays all comments for the post.
    """

    if current_user.username != username:
        return render_template("index.html.j2", title="Welcome", form=IndexForm())

    # Check if the username is alphanumerical and exists
    if not verify_username(username):
        return render_template("index.html.j2", title="Welcome", form=IndexForm())
    
    # check that it is an integer
    if not isinstance(post_id, int):
        return render_template("index.html.j2", title="Welcome", form=IndexForm())
    # check that it is positive
    if post_id < 0:
        return render_template("index.html.j2", title="Welcome", form=IndexForm())
    # check that the post exists
    
    get_post = f"""
        SELECT *
        FROM Posts AS p JOIN Users AS u ON p.u_id = u.id
        WHERE p.id = {post_id};
        """

    get_comments = f"""
        SELECT DISTINCT *
        FROM Comments AS c JOIN Users AS u ON c.u_id = u.id
        WHERE c.p_id={post_id}
        ORDER BY c.creation_time DESC;
        """
    
    post = sqlite.query(get_post, one=True)
    if post is None:
        return render_template("index.html.j2", title="Welcome", form=IndexForm())
    
    comments = sqlite.query(get_comments)

    comments_form = CommentsForm()
    get_user = f"""
        SELECT *
        FROM Users
        WHERE username = '{username}';
        """
    user = sqlite.query(get_user, one=True)

    if comments_form.is_submitted():

        # input validation
        if not xss_and_sqli_cehck(comments_form.comment.data):
            flash("Only alphanumeric characters and some punctuation (, . ! ? : -) is allowed ", category="warning")
            return render_template("comments.html.j2", title="Comments", username=username, form=comments_form, post=post, comments=comments)

        insert_comment = f"""
            INSERT INTO Comments (p_id, u_id, comment, creation_time)
            VALUES ({post_id}, {user["id"]}, '{comments_form.comment.data}', CURRENT_TIMESTAMP);
            """
        sqlite.query(insert_comment)

    return render_template(
        "comments.html.j2", title="Comments", username=username, form=comments_form, post=post, comments=comments
    )



@app.route("/friends/<string:username>", methods=["GET", "POST"])
@login_required
def friends(username: str):
    """Provides the friends page for the application.

    If a form was submitted, it reads the form data and inserts a new friend into the database.

    Otherwise, it reads the username from the URL and displays all friends of the user.
    """

    if current_user.username != username:
        return render_template("index.html.j2", title="Welcome", form=IndexForm())

    # Check if the username is alphanumerical and exists
    if not verify_username(username):
        return render_template("index.html.j2", title="Welcome", form=IndexForm())
    

    friends_form = FriendsForm()
    get_user = f"""
        SELECT *
        FROM Users
        WHERE username = '{username}';
        """
    user = sqlite.query(get_user, one=True)

    if friends_form.is_submitted():
        # check if alphanumerical
        if not friends_form.username.data.isalnum():
            flash("Only alphanumeric characters are allowed", category="warning")
            return render_template("friends.html.j2", title="Friends", username=username, form=friends_form)
        get_friend = f"""
            SELECT *
            FROM Users
            WHERE username = '{friends_form.username.data}';
            """
        friend = sqlite.query(get_friend, one=True)
        get_friends = f"""
            SELECT f_id
            FROM Friends
            WHERE u_id = {user["id"]};
            """
        friends = sqlite.query(get_friends)

        if friend is None:
            flash("User does not exist!", category="warning")
        elif friend["id"] == user["id"]:
            flash("You cannot be friends with yourself!", category="warning")
        elif friend["id"] in [friend["f_id"] for friend in friends]:
            flash("You are already friends with this user!", category="warning")
        else:
            insert_friend = f"""
                INSERT INTO Friends (u_id, f_id)
                VALUES ({user["id"]}, {friend["id"]});
                """
            sqlite.query(insert_friend)
            flash("Friend successfully added!", category="success")

    get_friends = f"""
        SELECT *
        FROM Friends AS f JOIN Users as u ON f.f_id = u.id
        WHERE f.u_id = {user["id"]} AND f.f_id != {user["id"]};
        """
    friends = sqlite.query(get_friends)
    return render_template("friends.html.j2", title="Friends", username=username, friends=friends, form=friends_form)



@app.route("/profile/<string:username>", methods=["GET", "POST"])
@login_required
def profile(username: str):
    """Provides the profile page for the application.

    If a form was submitted, it reads the form data and updates the user's profile in the database.

    Otherwise, it reads the username from the URL and displays the user's profile.
    """

    if current_user.username != username:
        return render_template("index.html.j2", title="Welcome", form=IndexForm())

    # Check if the username is alphanumerical and exists
    if not verify_username(username):
        return render_template("index.html.j2", title="Welcome", form=IndexForm())
    

    profile_form = ProfileForm()
    get_user = f"""
        SELECT *
        FROM Users
        WHERE username = '{username}';
        """
    user = sqlite.query(get_user, one=True)

    if profile_form.is_submitted():
        # profil update, input validation
        if not xss_and_sqli_cehck(profile_form.education.data):
            flash("Only alphanumeric characters and some punctuation (, . ! ? : -) is allowed ", category="warning")
            return render_template("profile.html.j2", title="Profile", username=username, user=user, form=profile_form)
        
        if not xss_and_sqli_cehck(profile_form.employment.data):
            flash("Only alphanumeric characters and some punctuation (, . ! ? : -) is allowed ", category="warning")
            return render_template("profile.html.j2", title="Profile", username=username, user=user, form=profile_form)
        
        if not xss_and_sqli_cehck(profile_form.music.data):
            flash("Only alphanumeric characters and some punctuation (, . ! ? : -) is allowed ", category="warning")
            return render_template("profile.html.j2", title="Profile", username=username, user=user, form=profile_form)
        
        if not xss_and_sqli_cehck(profile_form.movie.data):
            flash("Only alphanumeric characters and some punctuation (, . ! ? : -) is allowed ", category="warning")
            return render_template("profile.html.j2", title="Profile", username=username, user=user, form=profile_form)
        
        if not xss_and_sqli_cehck(profile_form.nationality.data):
            flash("Only alphanumeric characters and some punctuation (, . ! ? : -) is allowed ", category="warning")
            return render_template("profile.html.j2", title="Profile", username=username, user=user, form=profile_form)
        
        # check if date is valid, to prevent SQLI and XSS
        birthday = profile_form.birthday.data
        try:
            birthday = birthday.strftime("%Y-%m-%d")     
        except:
            flash("Invalid date format", category="warning")
            return render_template("profile.html.j2", title="Profile", username=username, user=user, form=profile_form)
        xss_and_sqli_cehck(birthday)

        update_profile = f"""
            UPDATE Users
            SET education='{profile_form.education.data}', employment='{profile_form.employment.data}',
                music='{profile_form.music.data}', movie='{profile_form.movie.data}',
                nationality='{profile_form.nationality.data}', birthday='{profile_form.birthday.data}'
            WHERE username='{username}';
            """
        sqlite.query(update_profile)
        return redirect(url_for("profile", username=username))
    # print("setting html nonce: ", g.nonce)
    g.nonce = generate_nonce()
    return render_template("profile.html.j2", title="Profile", username=username, user=user, form=profile_form, nonce=g.nonce)


@app.route("/uploads/<string:filename>")
def uploads(filename):
    """Provides an endpoint for serving uploaded files."""
    return send_from_directory(Path(app.instance_path) / app.config["UPLOADS_FOLDER_PATH"], filename)

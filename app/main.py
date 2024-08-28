import uuid
from threading import Timer
from email.policy import default

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, DateTime, ForeignKey, or_, and_,Float
from sqlalchemy.orm import Relationship
from sqlalchemy.sql.functions import user
from typing import List
import time

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "http://localhost:5173", "supports_credentials": True}})
db_config = {
    "host": 'localhost',
    "user": 'apps',
    "password": '1Mogesa#',
    "database": 'penzi_schema_rev'
  
   
}

app.config[
    'SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@localhost/{db_config['database']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True, nullable=False)
    phone_number = db.Column(db.String(15), unique=True, nullable=False)
    messages = Relationship('Message', backref='author', lazy='dynamic')
    name = db.Column(db.String(50), nullable=True)
    age = db.Column(db.Integer, nullable=True, default=18)
    gender = db.Column(db.String(50), nullable=True)
    county = db.Column(db.String(50), nullable=True)
    town = db.Column(db.String(50), nullable=True)
    education = db.Column(db.String(50), nullable=True)
    profession = db.Column(db.String(50), nullable=True)
    marital_status = db.Column(db.String(50), nullable=True)
    religion = db.Column(db.String(50), nullable=True)
    ethnicity = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)

    def to_json(self):
        return {
            'user_id': self.user_id,
            'phone_number': self.phone_number,
            'messages': self.messages
        }


class Message(db.Model):
    __tablename__ = 'messages'
    message_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    from_user_id = db.Column(db.Integer, ForeignKey('users.user_id'), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    message_content = db.Column(db.String(250), nullable=False)
    timestamp = db.Column(DateTime, default=func.now())
    shortcode = db.Column(db.String(45), nullable=False, default='22141')
    indexer=db.Column(Float,default=time.time(), nullable=True)

    def to_json(self):  # returns dictionary object of the message
        return {
            "phone_number": self.phone_number,
            "message_content": self.message_content,
            "timestamp": self.timestamp,
            "shortcode": self.shortcode,
            "from_user_id": self.from_user_id,
            "id": self.message_id
        }


with app.app_context():  # runs orm
    db.create_all()

org_short_code = '22141'

def create_org():
    org = db.session.query(User).filter_by(phone_number='22141').one_or_none()
    if org is None:
        new_org = User()
        new_org.phone_number = '22141'
        db.session.add(new_org)
        db.session.commit()
        return new_org.user_id
    return org.user_id


# initial sign in 
@app.route('/sign-in', methods=['POST'])
def sign_in():
    try:
        phone_number: str = request.get_json()['phone_number']
        if (not (phone_number.startswith('01')) and not (phone_number.startswith("07"))) or (len(phone_number) != 10):
            print(len(phone_number))
            return jsonify({'error': 'Invalid phone number'}), 400
        found = db.session.query(User).filter_by(phone_number=phone_number).one_or_none()
        if found is not None:
            response = jsonify()
            response.set_cookie('user_id', found.user_id)
            response.set_cookie('phone_number', found.phone_number)
            return jsonify({'message': "Welcome to Penzie!", "user": str(found.to_json())}), 400

        new_user = User()
        new_user.phone_number = phone_number

        db.session.add(new_user)
        db.session.commit()

        # generate default message
        default_msg = Message()
        default_msg.from_user_id = create_org()
        default_msg.message_content = "Welcome to Penzi our dating service with 6000 potential dating partners! To register SMS start#name#age#gender#county#town to 22141."
        default_msg.phone_number = new_user.phone_number
        default_msg.shortcode = org_short_code

        # persist
        db.session.add(default_msg)
        db.session.commit()

        # response = jsonify({'message': True, 'user': new_user.to_json()})
        response = jsonify()
        response.set_cookie('user_id', str(new_user.user_id))
        response.set_cookie('phone_number', phone_number)
        response.data = {'message': "Welcome to Penzi!", 'user': str(new_user.to_json())}
        return response
    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to register"}), 500


@app.route('/interact', methods=['POST'])
def register():
    try:
        cookie_id = request.cookies.get('user_id')
        user = db.session.query(User).filter_by(user_id=cookie_id).one_or_none()
        if user is None:
            return jsonify({"error": "Login and try again!"}), 400
        reg: str = request.get_json()['message']
        reg = reg.strip()
        # name#age#gender#county#town
        split = reg.split('#')
        if len(split) < 1:
            return jsonify({"error": "Invalid message"}), 400

        new_msg = Message()
        new_msg.from_user_id = cookie_id
        new_msg.phone_number = create_org()
        new_msg.message_content = reg
        db.session.add(new_msg)
        db.session.commit()
        sys_msg = Message()
        sys_msg.from_user_id = create_org()
        sys_msg.phone_number = user.phone_number
        sys_msg.shortcode = '22141'

        # if split[0].lower() == 'start' and len(split) == 6:
        if reg.lower().startswith('start'):
            # registration
            action, name, age, gender, county, town = split
            if name:
                user.name = name
            if age:
                user.age = age
            if gender:
                user.gender = gender
            if county:
                user.county = county
            if town:
                user.town = town
           # db.session.add(new_msg)
           # db.session.commit()
            # write a response message
            sys_msg.message_content = f"Your profile has been created successfully {name}.SMS details#levelOfEducation#profession#maritalStatus#religion#ethnicity to 22141.E.g. details#diploma#driver#single#christian#mijikenda"
            #db.session.add(sys_msg)
        if reg.lower().startswith('details'):
            # details#levelOfEducation#profession#maritalStatus#religion#ethnicity
            # write a response message
            if len(split) == 6:
                _details, education, profession, marital_status, religion, ethnicity = split
                user.education = education
                user.profession = profession
                user.marital_status = marital_status
                user.religion = religion
                user.ethnicity = ethnicity

                # write a response message
                sys_msg.message_content = "This is the last stage of registration. SMS a brief description of yourself to 22141 starting with the word MYSELF. E.g., MYSELF chocolate, lovely, sexy etc."

            else:
                sys_msg.message_content = "You were registered for dating with your initial details. To search for a MPENZI, SMS match#age#town to 22141 and meet the person of your dreams. E.g., match#23-25#Nairobi"
            #db.session.add(new_msg)
            #db.session.commit()
            #db.session.add(sys_msg)

        if reg.lower().startswith('myself'):
            print("here we go")
            user.description = reg
            sys_msg.message_content = "You are now registered for dating. To search for a MPENZI, SMS match#age#town to 22141 and meet the person of your dreams. E.g., match#23-25#Kisumu"
            #db.session.add(new_msg)
           # db.session.commit()
            #db.session.add(sys_msg)
        #db.session.commit() 
        db.session.add(sys_msg)
        db.session.commit()
        return jsonify()
    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to register"}), 500


@app.route('/match', methods=['POST'])
def match():
    try:
        text = request.get_json()['message']
        splits = text.split('#')
        if len(splits) != 3:
            return jsonify({"error": "Invalid message"}), 400
        _action, age, town = splits
        # split_age = list(int(age) for age in age.split("-"))
        split_age = list(int(age) for age in age.split("-"))
        split_age.sort()

        cookie_id = request.cookies.get('user_id') if request.cookies.get("user_id") else ""
        this_user = db.session.query(User).filter_by(user_id=cookie_id).one_or_none()
        if this_user is None:
            return jsonify({"error": "Login and try again!"}), 400

        found: List[User] = []
        # find users within that age range
        if len(split_age) > 1:
            found = db.session.query(User).filter(
                and_(User.age >= split_age[0], User.age <= split_age[1], User.town == town, User.gender != this_user.gender)
            ).all()
        elif len(split_age) == 1:
            found = db.session.query(User).filter(
                and_(User.age >= split_age[0], User.town == town, User.gender != this_user.gender)
            ).all()
        else:
            # Handle the case where split_age is empty
            found = db.session.query(User).filter(and_(User.town == town, User.gender != this_user.gender)).all()
        # save the user's message
        user_msg = Message()
        user_msg.from_user_id = request.cookies.get('user_id')
        user_msg.phone_number = org_short_code
        user_msg.message_content = text
        user_msg.shortcode = org_short_code
        db.session.add(user_msg)
        # save org response
        org_msg = Message()
        org_msg.from_user_id = create_org()
        org_msg.phone_number = request.cookies.get('phone_number')
        org_msg.message_content = f"Match Results: We have {len(found)} ladies who match your choice! We will send you details of 3 of them shortly. To get more details about a lady, SMS her number e.g., 0722010203 to 22141 "
        org_msg.shortcode = org_short_code
        db.session.add(org_msg)
        # add a list of the first 3 people who match
        if len(found) > 0:
            msg = ""
            for person in found[0:3]: # just the first 3
                msg += f"{person.name} aged {person.age}, {person.phone_number}\n"
            new_org_msg = Message()
            new_org_msg.from_user_id = create_org()
            new_org_msg.phone_number = request.cookies.get('phone_number')
            new_org_msg.message_content = msg
            new_org_msg.shortcode = org_short_code
            db.session.add(new_org_msg)
        db.session.commit()
        return jsonify({"message": "ok"}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to match, please try again!"}), 500


# fetch all messages
@app.route('/messages', methods=['GET'])
def get_messages():
    try:
        user_id = request.cookies.get('user_id')
        phone = request.cookies.get("phone_number")
        if not user_id:
            return jsonify({'error': 'Please log in again and try again!'}), 400
        messages = db.session.query(Message).order_by(Message.timestamp).filter(
            or_(Message.phone_number == phone, Message.from_user_id == user_id)).all()
        return jsonify(
            [message.to_json() for message in messages]), 200  # loop and convert  each messsage instance to dictionary
    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to fetch messages!"}), 500


# save message
@app.route("/save-message", methods=['POST'])
def save_message():
    try:
        data = request.get_json()
        # ensure all data is there
        invalid: bool = ("from_user_id" not in data) or ("phone_number" not in data) or (
                "message_content" not in data) or ("shortcode" not in data)
        if invalid:
            return jsonify({"error": "All fields are required!"}), 400
        new_message = Message()
        new_message.from_user_id = data['from_user_id']
        new_message.phone_number = data['phone_number']
        new_message.message_content = data['message_content']
        new_message.shortcode = data['shortcode']
        db.session.add(new_message)
        db.session.commit()

        return jsonify({"message": "Message saved"}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": "Sorry, something went wrong. Check input and try"}), 500


if __name__ == "__main__":
    app.run(debug=True)
    # create default org account
    create_org()

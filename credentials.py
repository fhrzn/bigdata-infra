from getpass import getpass
from dotenv import load_dotenv
import os
from requests import session
import db
from sqlalchemy.orm import sessionmaker

class Credentials():
    def __init__(self, email=None, pwd=None):
        # user auth credentials
        self.__email = email
        self.__pwd = pwd
        self.__li_at = None       

        # initialize db Session
        Session = sessionmaker(db.db)
        self.session = Session() 

        load_dotenv()
        # check mode
        if os.getenv('MODE') == 'DEV':
            self.__email = os.getenv('EMAIL')
            self.__pwd = os.getenv('PWD')
            # cookies
            try:
                cookie = os.getenv('LI_AT')
                if not cookie:
                    self.__li_at = cookie                    
            except:
                self.__li_at = None

        if not self.__email or not self.__pwd:
            print('Please insert your credentials')
            self.__prompt_credentials()

    def __prompt_credentials(self):
        self.__email = input('Email: ')
        self.__pwd = getpass(prompt='Password: ')    


    def get_uid(self):
        user = self.session.query(db.User)\
                            .filter(db.User.email == self.email).first()

        if not user:
            user = self.insert_user()

        return user.user_id

    def insert_user(self):
        user = db.User(email=self.email)
        self.session.add(user)
        self.session.commit()

        return user

    @property
    def email(self):
        return self.__email

    @email.setter
    def email(self, value):
        self.__email = value

    @property
    def password(self):
        return self.__pwd

    @password.setter
    def password(self, value):
        self.__pwd = value

    @property
    def li_at(self):
        if self.__li_at is None:
            print('WARNING - li_at value is None.')
        return self.__li_at

    @li_at.setter
    def li_at(self, value):
        self.__li_at = value
    
from flask import Flask, redirect, url_for, render_template, request, jsonify, flash
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func,  select, and_
import json
from flask_login import LoginManager, current_user, login_user, login_required, logout_user, UserMixin, login_manager
from flask_bcrypt import Bcrypt 

#Configure Flask app
app = Flask(__name__)
bcrypt = Bcrypt(app)
CORS(app)

#Configure DB
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///example.sqlite" 

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = "strong"

app.secret_key = 'keep it secret, keep it safe' # Add this to avoid an error

#set db variable as a SQLAlchemy obj tied to flask app "app"
db = SQLAlchemy(app) 

#Users DB - Contains ids, usernames, and passwords.
class Users(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
        username = db.Column(db.String, nullable=False)
        password = db.Column(db.String, nullable=False)

        #Function to check hashed password for validity -> used in /login
        def check_password(self, password):
            return bcrypt.check_password_hash(self.password, password)
        
        #Function to return the ID of the current user 
        def get_id(self):
           return (self.id)
        
        #How the object is represented on call
        def __repr__(self):
            return self.username

#Database class for gradebook -> contains students only: Contains row_id, id, student name, classname, and class grade
class Gradebook(UserMixin, db.Model):
    row_id = db.Column(db.Integer, primary_key=True, nullable=False)
    id = db.Column(db.Integer, nullable=False)
    studentName = db.Column(db.String, nullable=False)
    className = db.Column(db.String, db.ForeignKey('classes.className'), nullable=False)
    Grade = db.Column(db.Integer, nullable=False)
    class_name = db.relationship('Classes', backref=db.backref('studentName', lazy=True))
    def __repr__(self):
        return f'{self.studentName}'

#Database Class for class information, contains: class name, professor, timeInfo, capacity 
class Classes(UserMixin, db.Model):
    className = db.Column(db.String, primary_key=True, nullable=False)
    prof = db.Column(db.String, nullable=False)
    timeInfo = db.Column(db.String, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    def __repr__(self):
        return '<Classes %r>' % self.className

#enables us to call current user
@login_manager.user_loader
def load_user(id):
    return Users.query.get(int(id))

#Landing Page route, will go to login page
@app.route('/')
def renderIndex():
        #Display html file (**All html's go in templates -> CSS & JS go in static)
        return render_template("login.html")

#Route to open add/drop class page for a particular student 
@app.route('/addDrop', methods=['GET', 'POST'])
@login_required
def addDrop():
    #Get the id of the current user (student)
    _id = Users.get_id(current_user)

    #Get all classes this student enrolled in 
        #In database, this can be thought of as every time her names appears as a row in the table 
            #Returned variable _studentClasses is a list of objects that we can iterate through 
                #ANYTIME WE QUERY A DATABASE, IT WILL RETURN EITHER AN OBJECT OR LIST OF OBJECTS
                    #TYPE IS DEFINED BY TABLE BEING QUERIED
    _studentClasses = Gradebook.query.filter_by(id = _id).all()

    #Get all classes found in class DB 
    _allClasses = Classes.query.all()

    #Get the current counts for all classes 
    classStudentCounts = db.session.query(Gradebook.className, 
                      func.count(Gradebook.id).label('studentCount') 
                      ).group_by(Gradebook.className) 

    #Render the template for add_drop.html with all of the above queries passed through as arguments
        #These variables are received and usable within the HTML page via Jinja 
    return render_template("add_drop.html", studentName = current_user, classes=_allClasses, studentClasses=_studentClasses, studentCounts = classStudentCounts)

#Route to drop a student from the class
    #Args: classToDrop - name of a specific class
@app.route('/drop/<classToDrop>')
@login_required
def dropClass(classToDrop):

    #Get current logged-in user
    _id = Users.get_id(current_user)

    #Get all classes student is enrolled in 
    _studentClasses = Gradebook.query.filter_by(id = _id).all()

    hasClass = False
    rowID = None

    #check if classToDrop argument is within the classes the student is enrolled in 
    for _class in _studentClasses:
         if _class.className == classToDrop:
              hasClass = True
                #Mark the rowID where the enrolled student is found in gradebook
              rowID = _class.row_id
              break
         
    # print ("RowID"+str(rowID))

    #Coniditonal to check if student is enrolled in the class 
    if hasClass:
        #Begin database manipulation
         with app.app_context():
            #Get the row we want to delete from the table 
            entryToDelete = Gradebook.query.filter_by(row_id = rowID).first()

            #Delete the row from the table 
            if (entryToDelete):
                db.session.delete(entryToDelete)
                db.session.commit()
                #redirect to base user-page
                return redirect("/success/"+str(current_user))
            else:
                return redirect("/success/"+str(current_user))
            
#Route to add a student to a class 
    #Arguments: classToAdd - class name 
@app.route('/add/<classToAdd>')
@login_required
def addClass(classToAdd):

    #Get the id of the student logged in 
    _id = Users.get_id(current_user)

    #Get all classes student is enrolled in 
    _studentClasses = Gradebook.query.filter_by(id = _id).all()

    hasClass = False

    #Check if student is already enrolled in the class from the route argument 
    for _class in _studentClasses:
         if _class.className == classToAdd:
              hasClass = True
              break
         
    classFull = True

    #Get the class information from the Classes DB for the class from the route argument 
    _class = Classes.query.filter_by(className = classToAdd).first()

    #Get the count of each student in the class from the route argument
    studentsInClass =  db.session.query(Gradebook.id).filter(Gradebook.className == classToAdd).count()

    #Check if count of students in less than class capacity 
    if (studentsInClass < _class.capacity):
         classFull = False

    _allClasses = Classes.query.all()

    #Query to get each class and how many students are enrolled in each class
    classStudentCounts = db.session.query(Gradebook.className, 
                      func.count(Gradebook.id).label('studentCount') 
                      ).group_by(Gradebook.className)
         
    #if the student does not have the class, and the class is not full, let them enroll
    if (not hasClass) and (not classFull) :
         with app.app_context():
            
            #Get the max row_id value from the Gradebook table 
            maxRowID = db.session.query(func.max(Gradebook.row_id)).first()

            #use maxRowId to create a new primary key for our new entry into the gradebook DB 
            entryToAdd = Gradebook(row_id = (maxRowID[0]+1), id = int(_id), studentName = str(current_user), className = str(classToAdd), Grade = 0)

            #Commit entry to the db 
            if (entryToAdd):
                
                #Add new object to db
                db.session.add(entryToAdd)

                #Commit changes to db
                db.session.commit()
                #Redirect to home page for user
                return redirect("/success/"+str(current_user))
            else:
                return redirect("/success/"+str(current_user))
    #Error Handling 
    elif hasClass:
        _error = "Student Already Is Enrolled In Class"
        return render_template("add_drop.html", studentName = current_user, classes=_allClasses, studentClasses=_studentClasses, error = _error, studentCounts = classStudentCounts)
    elif classFull:
        _error = "Class is Full - Cannot Enroll at this Time"
        return render_template("add_drop.html", studentName = current_user, classes=_allClasses, studentClasses=_studentClasses, error = _error, studentCounts = classStudentCounts)
    else:
        _error = "Unkown command"
        return render_template("add_drop.html", studentName = current_user, classes=_allClasses, studentClasses=_studentClasses, error = _error, studentCounts = classStudentCounts) 



#Route to view all students in a particular class 
    #Arguments: _class - name of class to view students of 
@app.route('/viewStudents/<_class>')
@login_required
def viewStudents(_class):

        #Get all classes the current logged in user is an instructor for 
        taughtClasses = db.session.query(Classes).filter(Classes.prof == str(current_user)).all()

        #Check if the current user is an instructor for the _class from the argument
        for classRow in taughtClasses:
             if classRow.className == _class:

                #Get list of all rows in Gradebook where the classname = _class argument
                studentsInClass = db.session.query(Gradebook).filter(Gradebook.className == str(_class)).all()
                
                #Pass arguments to viewStudents and render
                return render_template("viewStudents.html", students = studentsInClass, className = _class, instructor = current_user)
        #Error handling/Security -> Prevents users that are not instructors from viewing the students in a class
        return 'You are not the instructor of that class'

#Route to initiate a grade change -> will confirm that the current user is the instructor of a class before redirecting to actual changeGrade page
    #Arguments: _studentName - Name of the student to change the grade for, _className - name of the class to change grade for 
@app.route('/changeGrade/<_studentName>/<_className>', methods = ['GET', 'POST'])
@login_required
def changeGrade(_studentName, _className):
        
        #Get all classes the current logged in user is an instructor for 
        taughtClasses = db.session.query(Classes).filter(Classes.prof == str(current_user)).all()

        #Check if the current user is an instructor for the _class from the argument
        for _class in taughtClasses:
             if _class.className == _className:
                    #Get Gradebook object (row) where the student name and classname from the arguments match 
                        #Will correspond to current grade student has for the class we're inquiring 
                    student = db.session.query(Gradebook).filter(and_(Gradebook.className == str(_class.className),Gradebook.studentName == str(_studentName) )).first()

                    # print(str(student) + str(student.Grade))
                    #Load the page to allow instructor to change the grade
                    return render_template("changeGrade.html", student = _studentName, className = student.className, currentGrade = student.Grade)
        #Error handling - Prevents anyone who is not the instructor of the argument class to see the page
        else:
            return 'ERROR - You are not authorized to change this grade'

#Route to change the grade within the Gradebook table for a particular student    
@app.route('/changeGrade/confirm/<studentName>/<_className>', methods = ['GET', 'POST'])
@login_required
def changeGradeConfirm(studentName, _className):
        
    #Clarrify post method
    if request.method == 'POST':

        #Ensure the current user is the instructor for the class 
        taughtClasses = db.session.query(Classes).filter(Classes.prof == str(current_user)).all()

        for _class in taughtClasses:
            if _class.className == _className:

                #Pull the new grade from the request form 
                newGrade = request.form['newGrade']

                with app.app_context():

                    #pull the Gradebook object matching the student and classname
                    student = db.session.query(Gradebook).filter(and_(Gradebook.className == str(_className),Gradebook.studentName == str(studentName) )).first()

                    #Assign the newGrade value from request data to the student object's grade attribute 
                    student.Grade = newGrade

                    #Commit Changes
                    db.session.commit() 
                    return redirect("/viewStudents/"+str(_className))
            #Error Handling 
            else: 
                return 'ERROR - You are not authorized to change this grade'  



#Route for main home page for a logged -in user
    #Will redirect to a different page depending on whether or not the current user is an instructor
        #Arguments - name - name of the logged in user **redundant since we can pull this info from current_user
@app.route('/success/<name>')
@login_required
def success(name):

        #Get all classed the current user is a prof for 
        taughtClasses = db.session.query(Classes).filter(Classes.prof == str(current_user)).all()

        #If user's name appears in the taughtClasses query, it implies they are an instructor 
        if taughtClasses:
            #Get all class names and student counts
            classStudentCounts = db.session.query(Gradebook.className, 
                                    func.count(Gradebook.id).label('studentCount') 
                                        ).group_by(Gradebook.className)
            #Render instructorView template with arguments plugged in
            return render_template("instructorView.html", content = name, rows=taughtClasses, studentCounts = classStudentCounts)
        
        #Case where user is a student 
        else:

            #Get the id of the current user 
            _id = Users.get_id(current_user)

            #Get all gradebook objects that match the current user's id =
                #(All classes student is enrolled in)
            x = Gradebook.query.filter_by(id = _id).all()

            # print(current_user)

            #Render template for student view, plug in arguments for current user's name and the classes they are enrolled in
            return render_template("studentView.html", content = name, rows=x)



#Route to let current user log out 
    #Redirects to landing/login page
@app.route('/logout', methods = ['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return render_template("login.html")

#Route to handle login
    #Routes to /success/<name> on successful login
@app.route('/login', methods=['GET', 'POST'])
def login():

    error = None
    _username = request.form['name']
    _password = request.form['password']

    if current_user.is_authenticated:
        return redirect(url_for('success',name = _username, password = _password))
    user = Users.query.filter_by(username=_username).first()
    if user is None or not user.check_password(_password):
        error = "Invalid Username or Password"
        flash("Incorrect Username or password")
        return render_template("login.html", error = error)
    else:
        login_user(user)
        return redirect(url_for('success',name = _username))

@app.route('/signUp')
def signUp():
    return render_template('signUpForm.html')

@app.route('/createAccount', methods=['POST'])
def createAccount():
     if request.method == 'POST':
        newName = request.form['newName']
        newPassword = request.form['newPassword']

        newPassword = bcrypt.generate_password_hash(newPassword).decode('utf-8') 

        with app.app_context():


            maxID = db.session.query(func.max(Users.id)).first()
            #Create new Gradebook object with value arguments
            newStudent = Users(id = (maxID[0]+1), username = newName, password=newPassword)

            #Add new object to db
            db.session.add(newStudent)

            #Commit changes to db
            db.session.commit()

            print("added student")

        print (newName + newPassword)

        return render_template("login.html")


if __name__ == '__main__':
 app.run()
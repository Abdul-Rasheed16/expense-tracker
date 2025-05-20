from flask import Flask, render_template, redirect, url_for, request, flash,session
from flask_mysqldb import MySQL
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"

#Database Configuration
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_DB']='authentication'
app.config['MYSQL_CURSORCLASS']='DictCursor'

mysql=MySQL(app)

#Home Page
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template("homepage.html")

#Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        con=mysql.connection.cursor()
        con.execute("SELECT * FROM user WHERE email = %s ", (email,))
        res=con.fetchone()
        con.close()

        if res:
            stored_hashed_password = res['password']
            entered_hashed_password = hashlib.sha256(password.encode()).hexdigest()


            if entered_hashed_password == stored_hashed_password:
                session['user_id'] = res['id']  # Save user ID in session
                session['username'] = res['username']
                return redirect('/dashboard')
            else:
                return "Invalid Email or Password!"
        else:
            return "Invalid Email or Password!"

    return render_template('login.html')



#Register Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Checking duplicate with user name
        con=mysql.connection.cursor()
        con.execute("select * from user where username=%s ",(username,))
        res=con.fetchone()
        print("The result from username", res)
        if res: # if the result is empty we can insert
            flash('Username already exists')
            return redirect('/register')
            
        # Checking duplicate with email
        con.execute("select * from user where email=%s ",(email,))
        res=con.fetchone()
        print("The result from email", res)
        if res: # if the result is empty we can insert
            flash('Email already exists')
            return redirect('/register')  

        # Password Hashing
        hashed_password = hashlib.sha256(password.encode()).hexdigest()    


        con.execute("INSERT INTO user (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed_password))
        mysql.connection.commit()
        con.close()

        flash("Successfully Registered!!")
        return redirect('/login')
    return render_template('register.html')   



@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')

    con = mysql.connection.cursor()

    # Get total spent per category
    con.execute("""
        SELECT category_name, SUM(amount) AS total_amount
        FROM expense
        WHERE user_id = %s AND is_deleted = 0
        GROUP BY category_name
    """, (user_id,))
    expenses_by_category = con.fetchall()

    # Get recent expenses
    con.execute("""
        SELECT DATE(created_at) AS date, category_name, amount
        FROM expense
        WHERE user_id = %s AND is_deleted = 0
        ORDER BY created_at DESC
        LIMIT 5
    """, (user_id,))
    recent_expenses = con.fetchall()

    con.close()

    # Prepare data for the chart
    categories = [row['category_name'] for row in expenses_by_category]
    amounts = [float(row['total_amount']) for row in expenses_by_category]

    return render_template('home.html', categories=categories, amounts=amounts, recent_expenses=recent_expenses)


#Budget Page

@app.route('/budget')
def budget():
    user_id = session.get('user_id')
    con = mysql.connection.cursor()
    sql = "SELECT id, budgetName, budget, startDate, endDate FROM budget WHERE user_id=%s AND is_deleted=0"
    con.execute(sql, (user_id,))
    res = con.fetchall()
    con.close()  # Close the cursor after fetching data

    formatted_data = [
        {
            'id': item['id'],
            'budgetName': item['budgetName'],
            'budget': item['budget'],
            'startDate': datetime.strptime(str(item['startDate']).split()[0], "%Y-%m-%d").strftime("%b-%d-%Y"),
            'endDate': datetime.strptime(str(item['endDate']).split()[0], "%Y-%m-%d").strftime("%b-%d-%Y")
        }
        for item in res
    ]

    return render_template('displaybudget.html', data=formatted_data)


#Add Budget

@app.route('/addbudget', methods=['GET', 'POST'])
def addbudget():
    if request.method == 'POST':
        budgetName = request.form['budgetName']
        budget = int(request.form['budget'])
        startDate = request.form['startDate']
        endDate = request.form['endDate']
        foodAllocation = int(request.form['foodAllocation'])
        transportation = int(request.form['transportation'])
        shopping = int(request.form['shopping'])
        entertainment = int(request.form['entertainment'])
        education = int(request.form['education'])
        other = int(request.form['other'])


        #Calculate total allocated amount
        total_allocated = foodAllocation + transportation + shopping + entertainment + education + other

        #Check if the total allocated budget exceeds monthly income
        if total_allocated > budget:
            flash("Total allocated amount exceeds monthly income! Please adjust your budget.")
            return redirect(url_for('addbudget')) #Redirect back to form


        con=mysql.connection.cursor()
        user_id = session.get('user_id')
        con.execute("INSERT INTO budget (budgetName, budget, startDate, endDate, foodAllocation, transportation, shopping, entertainment, education, other, user_id) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)",(budgetName, budget, startDate, endDate, foodAllocation, transportation, shopping, entertainment, education, other, user_id) )
        mysql.connection.commit()
        con.close()

        flash("Budget added successfully!")
        return redirect('/budget')
    return render_template('budget.html')
        
#Edit Budget

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    con=mysql.connection.cursor()


    if request.method == 'POST':
        budgetName = request.form['budgetName']
        budget = int(request.form['budget'])
        startDate = request.form['startDate']
        endDate = request.form['endDate']
        foodAllocation = int(request.form['foodAllocation'])
        transportation = int(request.form['transportation'])
        shopping = int(request.form['shopping'])
        entertainment = int(request.form['entertainment'])
        education = int(request.form['education'])
        other = int(request.form['other'])

        #Calculate total allocated amount
        total_allocated = foodAllocation + transportation + shopping + entertainment + education + other

        #Check if total allocated budget exceeds monthly income
        if total_allocated > budget:
            flash("Total allocated amount exceeds monthly income! Please adjust your budget.")
            return redirect(url_for('edit', id=id)) #Redirect back to form

        sql = "update budget set budgetName =%s, budget=%s, startDate=%s, endDate=%s, foodAllocation=%s, transportation=%s, shopping=%s, entertainment=%s, education=%s, other=%s where id=%s"
        con.execute(sql,[budgetName, budget, startDate, endDate, foodAllocation, transportation, shopping, entertainment, education, other, id])
        mysql.connection.commit()
        con.close()
        return redirect(url_for('budget'))
    
    #Fetching existing budget details for the edit form
    sql = "select * from budget where id=%s"
    con.execute(sql,[id,])
    res=con.fetchone()
    con.close()

    #Convert date format
    if res:
        res['startDate'] = datetime.strptime(str(res['startDate']).split()[0], "%Y-%m-%d").strftime("%Y-%m-%d")
        res['endDate'] = datetime.strptime(str(res['endDate']).split()[0], "%Y-%m-%d").strftime("%Y-%m-%d")
    return render_template('editbudget.html', data=res)


#Delete Budget
@app.route('/delete/<int:id>', methods=['GET', 'POST'])
def delete(id):
    con=mysql.connection.cursor()
    sql="update budget set is_deleted = 1 where id=%s"
    con.execute(sql,[id])
    mysql.connection.commit()
    con.close()
    return redirect(url_for('budget'))


#Budget Details
@app.route('/budget_details/<int:id>')
def budget_details(id):
    con = mysql.connection.cursor()
    
    # Fetch selected budget details
    con.execute("SELECT id, budgetName, budget, startDate, endDate FROM budget WHERE id=%s", (id,))
    budget = con.fetchone()

    if not budget:
        flash("Budget not found", "error")
        return redirect(url_for('budget'))

    # Fetch allocated budget per category
    con.execute("SELECT foodAllocation, transportation, shopping, entertainment, education, other FROM budget WHERE id=%s", (id,))
    allocated = con.fetchone() or {}

    # Use lowercase category keys matching DB
    categories = ["foodAllocation", "transportation", "shopping", "entertainment", "education", "other"]

    allocated_dict = {cat: int(allocated.get(cat, 0)) for cat in categories}

    # Fetch spent amount per category from expense table
    con.execute("SELECT category_name, SUM(amount) as spent FROM expense WHERE budget_id=%s GROUP BY category_name", (id,))
    expenses = con.fetchall()
    con.close()

    spent_dict = {row["category_name"]: row["spent"] for row in expenses if row["spent"] is not None}

    category_data = []
    for category in categories:
        allocated_amount = allocated_dict.get(category, 0)
        spent_amount = spent_dict.get(category, 0)
        remaining_amount = allocated_amount - spent_amount

        # Display name: make it readable
        display_name = category[0].upper() + category[1:]  # or customize if needed

        category_data.append({
            'category': display_name,
            'allocated': allocated_amount,
            'spent': spent_amount,
            'remaining': remaining_amount
        })

    return render_template("budgetDetails.html", budget=budget, category_data=category_data)


#Budget Report
@app.route('/budget_report')
def budget_report():
    user_id = session.get('user_id')  # Get current user ID
    con = mysql.connection.cursor()

    # 1. Fetch total spent amount per category (for Bar Chart)
    con.execute("""
        SELECT category_name, SUM(amount) AS total_spent
        FROM expense
        WHERE is_deleted = 0 AND user_id = %s
        GROUP BY category_name
    """, (user_id,))
    category_expenses = con.fetchall()

    # 2. Fetch budget vs total spent (for Line Chart)
    con.execute("""
        SELECT b.budgetName, b.budget, 
               IFNULL(SUM(e.amount), 0) as total_spent
        FROM budget b
        LEFT JOIN expense e 
            ON b.id = e.budget_id AND e.is_deleted = 0
        WHERE b.is_deleted = 0 AND b.user_id = %s
        GROUP BY b.id
    """, (user_id,))
    budget_tracking = con.fetchall()

    con.close()

    # Prepare Bar Chart data (Expense by Category)
    categories = [row['category_name'] for row in category_expenses]
    spent_amounts = [row['total_spent'] for row in category_expenses]

    # Prepare Line Chart data (Budget vs Spent)
    budget_names = [row['budgetName'] for row in budget_tracking]
    total_budgets = [row['budget'] for row in budget_tracking]
    total_spent = [row['total_spent'] for row in budget_tracking]

    return render_template('budgetReport.html', 
                           categories=categories,
                           spent_amounts=spent_amounts,
                           budget_names=budget_names,
                           total_budgets=total_budgets,
                           total_spent=total_spent)



#Expense Page

@app.route('/expense')
def expense():
    user_id = session.get('user_id')
    con=mysql.connection.cursor()
    sql ="Select * from expense where user_id=%s and is_deleted=0"
    con.execute(sql, (user_id,))
    res=con.fetchall()
    return render_template('displayexpense.html', data=res)




#Add Expense

@app.route('/addexpense', methods=['GET', 'POST'])
def addexpense():
    user_id = session.get('user_id')
    con = mysql.connection.cursor()

    if request.method == 'POST':
        category_name = request.form['category_name']
        amount = int(request.form['amount'])
        description = request.form['description']
        budget_id = int(request.form['budget_id'])

        # Fetch the selected budget's category allocation
        con.execute(f"SELECT {category_name} FROM budget WHERE id = %s AND user_id = %s AND is_deleted = 0", (budget_id, user_id))
        budget_res = con.fetchone()

        if not budget_res:
            con.close()
            return render_template('expense.html', error="Invalid budget selection.")

        allocated_amount = int(budget_res[category_name])

        if allocated_amount < amount:
            con.close()
            return render_template('expense.html', error=f"Not enough budget for {category_name}. Available: {allocated_amount}, Required: {amount}")

        # Update the allocated budget
        new_allocated_amount = allocated_amount - amount
        con.execute(f"UPDATE budget SET {category_name} = %s WHERE id = %s", (new_allocated_amount, budget_id))

        # Insert the expense
        con.execute("INSERT INTO expense (category_name, amount, description, budget_id, user_id) VALUES (%s, %s, %s, %s, %s)",
                    (category_name, amount, description, budget_id, user_id))

        mysql.connection.commit()
        con.close()
        return redirect('/expense')

    # GET method: fetch all available budgets
    con.execute("SELECT id, budgetName FROM budget WHERE user_id = %s AND is_deleted = 0", (user_id,))
    budgets = con.fetchall()
    con.close()

    return render_template('expense.html', budgets=budgets)


#Edit Expense

@app.route('/editexpense/<int:id>', methods=['GET', 'POST'])
def editexpense(id):
    user_id = session.get('user_id')
    con = mysql.connection.cursor()

    if request.method == 'POST':
        category_name = request.form['category_name']
        amount = request.form['amount']
        description = request.form['description']
        budget_id = request.form['budget_id']

        sql = "UPDATE expense SET category_name=%s, amount=%s, description=%s, budget_id=%s WHERE id=%s AND user_id=%s"
        con.execute(sql, [category_name, amount, description, budget_id, id, user_id])
        mysql.connection.commit()
        con.close()
        return redirect(url_for('expense'))

    # Fetch existing expense data
    con.execute("SELECT * FROM expense WHERE id=%s AND user_id=%s", (id, user_id))
    expense_data = con.fetchone()

    # Fetch available budgets
    con.execute("SELECT id, budgetName FROM budget WHERE user_id = %s AND is_deleted = 0", (user_id,))
    budgets = con.fetchall()
    con.close()

    return render_template('editexpense.html', data=expense_data, budgets=budgets)

#Delete Expense

@app.route('/deleteexpense/<int:id>', methods=['GET', 'POST'])
def deleteexpense(id):
    user_id = session.get('user_id')
    con = mysql.connection.cursor()

    # Ensure the expense belongs to the current user
    con.execute("SELECT * FROM expense WHERE id=%s AND user_id=%s", (id, user_id))
    res = con.fetchone()
    if not res:
        flash("Unauthorized action.")
        return redirect(url_for('expense'))

    con.execute("UPDATE expense SET is_deleted = 1 WHERE id=%s", (id,))
    mysql.connection.commit()
    con.close()
    return redirect(url_for('expense'))


#logout
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.")
    return redirect(url_for('login'))







if __name__ == '__main__':
    app.run(debug=True)    
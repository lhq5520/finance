import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
uri = os.getenv("postgres://kwppywdlarguoi:9b739ff12b75b218772a017cc7528bc9f43db144f07c24e98382e94efa46ae32@ec2-52-0-142-65.compute-1.amazonaws.com:5432/dbi5248uo1inn0?sslmode=allow")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://")
db = SQL(uri)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    id = session['user_id']

    purchased_stock = db.execute("SELECT symbol, company_name, shares FROM stock WHERE user_id = ? ORDER BY symbol", id)
    stock_info = []

    stock_price = []
    stock_total = []

    for row in range(len(purchased_stock)):
        temp1 = lookup(purchased_stock[row]["symbol"])
        stock_info.append(temp1)

    for row in range(len(purchased_stock)):
        temp2 = float(stock_info[row]["price"])
        temp3 = float(purchased_stock[row]["shares"])
        temp_price = temp2 * temp3
        stock_price.append(temp2)
        stock_total.append(temp_price)

    total_cash = db.execute("SELECT cash FROM users WHERE id = ?", id)
    total_amount = total_cash[0]["cash"]
    for row in range(len(purchased_stock)):
        total_amount = total_amount + stock_total[row]

    return render_template("index.html", purchased_stock=purchased_stock, stock_info=stock_info, stock_price=stock_price, stock_total=stock_total, total_cash=total_cash, total_amount=total_amount)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        # display form to buy a stock
        return render_template("buy.html")

    if request.method == "POST":

        # Purchase the stock so long as the user can afford it
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        stock_info = lookup(symbol)
        if not symbol or not shares:
            return apology("please fill out symbol or shares, or symbol does not exist ", 400)
        if not lookup(symbol):
            return apology("symbol does not exist ", 400)
        try:
            shares = int(shares)
        except ValueError:
            return apology("Shares can only be integers ", 400)

        if not isinstance(shares, int):
            return apology("Shares can only be numbers ", 400)
        if shares < 0:
            return apology("Shares can not be negative ", 400)

        # Purchase the stock so long as the user can afford it
        stock_symbol = stock_info["symbol"]
        stock_company = stock_info["name"]
        stock_price = stock_info["price"]
        id = session['user_id']
        cash = db.execute("SELECT cash FROM users WHERE id = ?", id)
        total_price = stock_price * int(shares)

        # update cash and insert into transation
        if total_price > cash[0]["cash"]:
            return apology("You do not have enough cash ", 400)
        else:
            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash[0]["cash"] - total_price, id)
            db.execute("INSERT INTO buyer (user_id, symbol, company_name, price, shares) VALUES (?, ?, ?, ?, ?)",id, stock_symbol, stock_company, stock_price, shares) # insert purchase transaction

            # update count(prices, shares) of a stock
            checker = db.execute("SELECT symbol FROM stock WHERE symbol = ? AND user_id = ?",symbol, id)

            if len(checker) == 0:
                db.execute("INSERT INTO stock (user_id, symbol, company_name, price, shares) VALUES (?, ?, ?, ?, ?)",id, stock_symbol, stock_company, stock_price, shares) #insert stock(count)

            elif len(checker) != 0:
                total_share = db.execute("SELECT shares FROM stock WHERE symbol = ? AND user_id = ?", symbol, id)
                db.execute("UPDATE stock SET shares = ?, price = ?, company_name = ? WHERE symbol = ? AND user_id = ?", total_share[0]["shares"] + int(shares), stock_price, stock_company, stock_symbol, id)

    return redirect("/")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    id = session['user_id']
    stock_info = db.execute("SELECT * FROM buyer WHERE user_id = ?", id)

    return render_template("history.html", stock_info=stock_info)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "GET":
        # display form to request a stock quote
        return render_template("quote.html")

    if request.method == "POST":
        # lookup the stock symbol by calling the lookup function, and display the results
        symbol = request.form.get("symbol").upper()
        if not symbol:
            return apology("please enter a symbol", 400)

        symbol_info = lookup(symbol)
        if symbol_info:
            return render_template("quoted.html", symbol_info=symbol_info)

        if not symbol_info:
            return apology("stock symbol doesn't exist", 400)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        # display a registration form to user
        return render_template("register.html")

    if request.method == "POST":
        # check for possible errors
        username = request.form.get("username")
        password = request.form.get("password")
        password2 = request.form.get("confirmation")

        checker = db.execute("SELECT * FROM users WHERE username = ? ", username)
        if not username or not password or not password2:
            return apology("Please make sure no form left blank", 400)
        if password != password2:
            return apology("Please confirm that your password is consistent", 400)

        if len(checker) != 0:
            return apology("Username exists. Please change to another one", 400)

        # insert the new user into user table
        else:
            hash_password = generate_password_hash(password)
            db.execute("INSERT INTO users (username, hash) VALUES (?,?)", username, hash_password)

        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    id = session['user_id']

    """Sell shares of stock"""
    if request.method == "GET":
        # display form to sell a stock
        purchased_stock = db.execute("SELECT symbol FROM stock WHERE user_id = ? ORDER BY symbol", id)
        return render_template("sell.html", purchased_stock=purchased_stock)

    if request.method == "POST":
        shares = request.form.get("shares")
        symbol = request.form.get("symbol")
        selection = db.execute("SELECT shares FROM stock WHERE symbol = ? AND user_id = ? ORDER BY symbol", symbol, id)
        # check for erros and sell the specified number of shares of stock and update the user's cash
        if not shares:
            return apology("please enter how many shares of stock you want to sell ", 400)
        if not symbol:
            return apology("please select a symbol you want to sell", 400)
        if int(shares) > int(selection[0]["shares"]):
            return apology("you do not have enough shares of stock", 400)
        else:

            stock_info = lookup(symbol)
            stock_symbol = stock_info["symbol"]
            stock_company = stock_info["name"]
            stock_price = stock_info["price"]

            # make sure that 0 shares of stock gets delete
            checker = db.execute("SELECT symbol FROM stock WHERE shares = 0")
            if len(checker) != 0:
                db.execute("DELETE FROM stock WHERE shares = 0")

            # update count(prices, shares) of a stock
            if int(selection[0]["shares"]) != 0:
                total_share = db.execute("SELECT shares FROM stock WHERE symbol = ? AND user_id = ?", symbol, id)
                db.execute("UPDATE stock SET shares = ? WHERE symbol = ? AND user_id = ?", total_share[0]["shares"] - int(shares), stock_symbol, id)

            # update cash and insert into transation
            cash = db.execute("SELECT cash FROM users WHERE id = ?", id)
            total_price = stock_price * int(shares)

            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash[0]["cash"] + total_price, id)
            db.execute("INSERT INTO buyer (user_id, symbol, company_name, price, shares) VALUES (?, ?, ?, ?, ?)",id, stock_symbol, stock_company, stock_price, -abs(int(shares)))  # insert selling transaction

            # make sure that 0 shares of stock gets delete
            db.execute("DELETE FROM stock WHERE shares = 0")

    return redirect("/")
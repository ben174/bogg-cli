import datetime
import calendar

import click
import requests

import bogg_utils

@click.command()
@click.option('--ate/--exercised', default=True, help="Ate or Exercised (default: Ate)")
@click.option('--date', default=datetime.date.today(), help="Date in which entry occurred.")
@click.argument('calories', required=False)
@click.argument('note', required=False)
def cli(ate, calories, note, date):
    """Command line interface for bo.gg

    Examples:

       bogg 100                    (I ate 100 calories)

       bogg 300 sandwich           (I ate a 300-calorie sandwich)

       bogg --exercised 200 bike   (I rode my bike and worked off 200 calories)

       bogg sunset-jog             (Log my sunset jog, which I've pre-defined in my lookups)

    """
    bogg_utils.CURRENT_DATE = date
    if not bogg_utils.TOKEN:
        setup()

    if not calories:
        while interactive():
            pass
        return

    if calories.isdigit():
        calories = int(calories)
    else:
        raise NotImplementedError('Lookups aren\'t done yet.')

    create_entry(calories, note, ate)


def setup():
    click.echo('Welcome to bo.gg!')
    click.echo('')
    click.echo('1: Existing user')
    click.echo('2: New user')
    click.echo('')
    click.echo('Command? ', nl=False)
    while True:
        c = click.getchar()
        if c.isdigit():
            break
        click.echo('Invalid option.')

    click.echo()
    c = int(c)
    if c == 1:
        if not prompt_login():
            exit()
    else:
        enrollment()

def log():
    pass

def add_shortcut(calories, note):
    pass

def enrollment():
    '''
    {
        "username": "ben16",
        "email": "ben189@gmail.com",
        "password": "balls",
        "daily_weight_goal": 0.2,
        "height": 72,
        "weight": 270,
        "activity_factor": 1.2,
        "bogger": {
            "gender": "M",
            "birthdate": "1985-11-23",
            "auto_update_goal": true
        }
    }
    '''
    username = click.prompt('Choose a username')
    email = click.prompt('Enter your email')
    while True:
        password = click.prompt('Choose a password', hide_input=True)
        confirm_password = click.prompt('Confirm password', hide_input=True)
        if password == confirm_password:
            break
        click.echo('Passwords do not match. Try again.')
    weekly_goal = click.prompt('How many pounds do you want to lose per week? (Usually between 1.0 and 2.0)',
                               type=float)
    daily_weight_goal = round(weekly_goal / 7.0, 3)
    click.echo()
    click.echo('The following questions are only used to calculate your basic metabolic rate and figure out ' \
               'how many calories you should be eating per day.')
    click.echo()
    click.echo('Activity Level (https://en.wikipedia.org/wiki/Physical_activity_level)')
    click.echo()
    click.echo('  1. Sedentary')
    click.echo('  2. Lightly Active')
    click.echo('  3. Moderately Active')
    click.echo('  4. Very Active')
    click.echo('  5. Extra Active')
    click.echo()
    click.echo('Enter your activity level: ', nl=False)
    while True:
        c = click.getchar()
        if c.isdigit():
            break
        click.echo('Invalid option. Enter 1-5.')
    c = int(c)
    activity_factor = 1.2
    if c == 1:
        activity_factor = 1.2
    elif c == 2:
        activity_factor = 1.375
    elif c == 3:
        activity_factor = 1.55
    elif c == 4:
        activity_factor = 1.725
    elif c == 5:
        activity_factor = 1.9

    click.echo()
    click.echo('Gender (m/f): ', nl=False)
    while True:
        gender = click.getchar().upper()
        if gender in ('M', 'F'):
            break
        click.echo('Invalid option. Enter m or f.')
    click.echo()

    birthdate = click.prompt('Enter your birthdate (YYYY-MM-DD)')
    height = click.prompt('Enter your height (in inches)', type=int)
    weight = click.prompt('Enter your weight (in pounds)', type=int)
    click.echo()
    payload = {
        'username': username,
        'email': email,
        'password': password,
        'daily_weight_goal': daily_weight_goal,
        'height': height,
        'weight': weight,
        'activity_factor': activity_factor,
        'bogger': {
            'gender': gender,
            'birthdate': birthdate,
            'auto_update_goal': True
        }
    }

    data = enroll_user(payload)

    bogg_utils.USERNAME = username
    token = bogg_utils.retrieve_token(password)

    click.echo('User: {} created. Your daily calorie goal is: {}'.format(
        data['username'],
        data['bogger']['current_calorie_goal']
    ))
    click.echo()
    click.echo('You are now ready to start logging. Simply run \'bogg\' from your ' +
               'command line to start logging!')

def enroll_user(payload):
    while True:
        response = requests.post(
            '{}/api/create/'.format(bogg_utils.API_BASE),
            json=payload,
        )
        try:
            response.raise_for_status()
            return response.json()
        except:
            data = response.json()
            for field in data.keys():
                click.echo('Invalid {} ({}): {}'.format(
                    field,
                    payload[field],
                    ', '.join(data[field]),
                ))
                new_val = click.prompt('Enter another {}'.format(field))
                payload[field] = new_val


def prompt_login():
    bogg_utils.USERNAME = click.prompt('Username')
    password = click.prompt('Password', hide_input=True)
    try:
        bogg_utils.retrieve_token(password)
    except requests.exceptions.HTTPError as ex:
        if ex.response.status_code == 400:
            click.echo('Invalid login')
            return False
        else:
            raise
    del password
    return True

def create_measurement(weight):
    raise NotImplementedError('Weight measurement not implemented.')

def create_entry(calories, note, ate=True, dt_occurred=None):
    if not ate:
        calories = calories * -1

    payload = {
        'entry_type': 'C' if ate else 'E',
        'calories': calories,
        'note': note,
        'dt_occurred': str(bogg_utils.CURRENT_DATE)
    }

    if not note:
        payload['note'] = 'Command line entry with no note.'

    response = requests.post(
        '{}/api/entries/'.format(bogg_utils.API_BASE),
        headers={'Authorization': 'Token {}'.format(bogg_utils.TOKEN)},
        json=payload,
    )

    try:
        response.raise_for_status()
    except:
        print payload
        print response.content
        print response
        exit()

    click.echo(click.style('Logged {} calories.'.format(calories), fg='green'))
    show_status()

def show_status():
    date_string = datetime.date.today()
    response = requests.get(
        '{}/api/daily/{}'.format(bogg_utils.API_BASE, date_string),
        headers={'Authorization': 'Token {}'.format(bogg_utils.TOKEN)},
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        if response.status_code == 404:
            click.echo(' - No log entries for today.')
            return
        else:
            raise
    data = response.json()

    click.echo(' - You have eaten {} calories.'.format(data['calories_consumed']))
    click.echo(' - You have burned off {} calories.'.format(abs(data['calories_expended'])))
    if data['calories_remaining'] > 0:
        message = 'You can eat {} more calories today.'.format(data['calories_remaining'])
        click.echo(
            click.style(message, fg='green')
        )
    elif data['calories_remaining'] < 0:
        message = 'You have exceeded your goal by {} calories.'.format(abs(data['calories_remaining']))
        click.echo(
            click.style(message, fg='red')
        )
    else:
        message = 'You are exactly at your calorie goal.'
        click.echo(
            click.style(message, fg='green')
        )


def show_log():
    response = requests.get(
        '{}/api/daily/'.format(bogg_utils.API_BASE),
        headers={'Authorization': 'Token {}'.format(bogg_utils.TOKEN)},
    )
    data = response.json()['results']
    for entry in data:
        ''' "date": "2016-05-11",
        "calories_consumed": 100,
        "calories_expended": 0,
        "net_calories": 100,
        "calories_remaining": null
        '''
        click.echo('{}: {} eaten, {} exercised, {} remaining.'.format(
            entry['date'],
            entry['calories_consumed'],
            entry['calories_expended'],
            entry['calories_remaining'],
        ))


def draw_calendar():
    click.echo('Su Mo Tu We Th Fr Sa')
    dates = calendar.monthcalendar(
        bogg_utils.CURRENT_DATE.year,
        bogg_utils.CURRENT_DATE.month
    )
    for week in dates:
        for day in week:
            if day == 0:
                click.echo('   ', nl=False)
            else:
                click.echo(str(day).ljust(3), nl=False)
        click.echo()


def interactive_menu():
    dateline = 'Currently entering data for: {}'.format(bogg_utils.CURRENT_DATE)
    click.echo(dateline)
    click.echo('- Use [ / ] to page through dates.')
    click.echo()
    click.echo('1: Log calories eaten.')
    click.echo('2: Log calories exercised.')
    click.echo('3: Record a new weight measurement.')
    click.echo('4: Select another date.')
    click.echo('5: Add an item to your quick-lookups.')
    click.echo('6: View status for today.')
    click.echo('7: View a log of the past few days.')
    click.echo('8: Edit configuration.')
    click.echo()
    click.echo('?: This menu.')
    click.echo('Q: Quit.')
    click.echo()

def interactive():
    interactive_menu()
    while True:
        click.echo('Command? ', nl=False)
        c = click.getchar().lower()
        valid_commands = [str(i) for i in range(9)] + ['[', ']', 'q', '?']
        if c in valid_commands:
            if c == '?':
                interactive_menu()
            elif c == 'q':
                quit()
            elif c == '[' or c == ']':
                delta = 1 if c == ']' else -1
                bogg_utils.CURRENT_DATE += datetime.timedelta(days=delta)
                interactive_menu()
            else:
                click.echo()
                c = int(c)
                process_command(c)
        else:
            click.echo('Invalid option.')

def process_command(c):
    if c == 1 or c == 2:
        ate = c == 1
        calories = click.prompt('Number of calories', type=int)
        action = "eat" if ate else "do"
        note = click.prompt('What did you {}?'.format(action))
        create_entry(calories, note, ate)
    elif c == 3:
        weight = click.prompt('Enter your new weight', type=int)
        create_entry(weight)
    elif c == 4:
        #TODO: Lookup items via pager
        pass
    elif c == 5:
        click.echo('(F)ood or (E)xercise? ')
        c = click.getchar().lower()
        ate = c == 'F'
        calories = click.prompt('Number of calories', type=int)
        note = click.prompt('Name this entry')
        create_entry(calories, note, ate)
        add_shortcut(calories, note)
    elif c == 6:
        show_status()
    elif c == 7:
        show_log()
    elif c == 8:
        click.edit(filename=bogg_utils.CONFIG_PATH)
    elif c == 9:
        return False
    return True

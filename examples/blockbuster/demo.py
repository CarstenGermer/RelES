from __future__ import absolute_import, print_function

import json
from time import sleep
from uuid import uuid4

import click
import requests


@click.pass_context
def _make_document(ctx, doc_type, **kwargs):
    res = ctx.obj['session'].post(
        '{}/{}/{}/'.format(ctx.obj['HOST'], ctx.obj['INDEX'], doc_type),
        json=kwargs
    )
    res.raise_for_status()

    return res.json()


@click.pass_context
def _update_document(ctx, doc_type, id, **kwargs):
    res = ctx.obj['session'].put(
        '{}/{}/{}/{}'.format(ctx.obj['HOST'], ctx.obj['INDEX'], doc_type, id),
        json=kwargs
    )
    res.raise_for_status()

    return res.json()

@click.pass_context
def _uploaded_file(ctx, file_path, mime_type='image/jpeg'):
    res = ctx.obj['session'].post(
        '{}/cdn/files/'.format(ctx.obj['HOST']),
        files={'file': ('random.txt', open(file_path, 'rb'), mime_type)},
        allow_redirects=False
    )
    res.raise_for_status()

    return res.json()


@click.pass_context
def _geocode_address(ctx, address):
    res = ctx.obj['session'].get(
        '{}/geocode'.format(ctx.obj['HOST']),
        params={'address': address},
    )
    res.raise_for_status()

    return res.json()


@click.group()
@click.option('--jwt', required=True, help='Json Web Token (JWT) to use')
@click.option('--host', default='localhost:9999', help='target hostname (default: localhost:9999)')
@click.option('--index', default='blockbuster', help='target index (default: blockbuster)')
@click.pass_context
def demo(ctx, jwt, host, index):
    ctx.obj['HOST'] = 'http://%s' % host
    ctx.obj['INDEX'] = index
    ctx.obj['JWT'] = jwt
    ctx.obj['session'] = requests.Session()
    ctx.obj['session'].headers.update({'Authorization': 'Bearer %s' % jwt.strip()})


@demo.command()
def enum():
    """Demonstrate *enum* property validation"""

    click.secho('*** Creating Movie to create a BlueRay for...', fg='green')
    crow = _make_document('movie', title='The Crow')
    click.secho(json.dumps(crow, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Trying to create a BlueRay with an *invalid* region code...', fg='green')
    try:
        _make_document('blueray', movie_id=crow['_id'], region_code='D')
    except requests.HTTPError as e:
        click.secho(str(e), fg='red')
        click.secho(json.dumps(e.response.json(), indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Trying to create a BlueRay with a *valid* region code...', fg='green')
    blueray = _make_document('blueray', movie_id=crow['_id'], region_code='FREE')
    click.secho(json.dumps(blueray, indent=2, sort_keys=True), fg='yellow')


@demo.command()
def file_upload():
    """Demonstrate uploading a file and attaching it to a document"""

    click.secho('*** Uploading image...', fg='green')
    uploaded = _uploaded_file('cover.jpg')
    click.secho(json.dumps(uploaded, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Creating a Picture document for it...', fg='green')
    picture = _make_document('picture', title='cover image', sys_filename=uploaded['path'])
    click.secho(json.dumps(picture, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Attaching it to a Blueray as cover...', fg='green')
    slp = _make_document('movie', title='Silver Linings Playbook')
    blueray = _make_document('blueray', movie_id=slp['_id'], cover_id=picture['_id'])
    click.secho(json.dumps(blueray, indent=2, sort_keys=True), fg='yellow')


@demo.command()
def fill_from_fkey():
    """Demonstrate *fill_from_fkey* document processor"""

    click.secho('*** Creating Movie to create a BlueRay for...', fg='green')
    fight_club = _make_document('movie', title='Fight Club')
    click.secho(json.dumps(fight_club, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Creating BlueRay with movie_id, movie should get embedded...', fg='green')
    blueray = _make_document('blueray', movie_id=fight_club['_id'])
    click.secho(json.dumps(blueray, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Creating User to rent it out to...', fg='green')
    mcclane = _make_document('user', email='mcclane-{}@example.net'.format(uuid4().hex), age=33)
    click.secho(json.dumps(mcclane, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Renting it out, renter_email should get embedded...', fg='green')
    rental = _make_document('rental', rented_by=mcclane['_id'], rented_on='1988-07-20 20:15:00', return_before='1990-07-04 22:15:00')
    click.secho(json.dumps(rental, indent=2, sort_keys=True), fg='yellow')


@demo.command()
def include_parents():
    """Demonstrate *include_parents* document processor"""
    suffix = uuid4().hex

    click.secho('*** Creating Genres for Movie...', fg='green')
    _horror = _make_document('genre', name='Horror - %s' % suffix)
    click.secho(json.dumps(_horror, indent=2, sort_keys=True), fg='yellow')

    _monster = _make_document('genre', name='Monster - %s' % suffix, parent=_horror['_id'])
    click.secho(json.dumps(_monster, indent=2, sort_keys=True), fg='yellow')

    _vampire = _make_document('genre', name='Vampire - %s' % suffix, parent=_monster['_id'])
    click.secho(json.dumps(_vampire, indent=2, sort_keys=True), fg='yellow')

    _werewolf = _make_document('genre', name='Werewolf - %s' % suffix, parent=_monster['_id'])
    click.secho(json.dumps(_werewolf, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Creating Movie with genres `Werewolf` and `Vampire`, parent genres should be auto-filled...', fg='green')
    twilight = _make_document('movie', title='Twilight', genres=[_vampire['_id'], _werewolf['_id']])
    click.secho(json.dumps(twilight, indent=2, sort_keys=True), fg='yellow')


@demo.command()
def minmax():
    """Demonstrate *minimum/maximum* pattern validation"""

    click.secho('*** Trying to create a Movie with an *invalid* imdb rating...', fg='green')
    try:
        _make_document('movie', title='300', imdb_rating=-1)
    except requests.HTTPError as e:
        click.secho(str(e), fg='red')
        click.secho(json.dumps(e.response.json(), indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Trying to create another Movie with an *invalid* imdb rating...', fg='green')
    try:
        _make_document('movie', title='300', imdb_rating=11)
    except requests.HTTPError as e:
        click.secho(str(e), fg='red')
        click.secho(json.dumps(e.response.json(), indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Creating a movie *with* a valid imdb rating...', fg='green')

    threehundred = _make_document('movie', title='300', imdb_rating=9)
    click.secho(json.dumps(threehundred, indent=2, sort_keys=True), fg='yellow')


@demo.command()
def regex():
    """Demonstrate *regex* pattern validation"""

    click.secho('*** Creating Movie to create a BlueRay for...', fg='green')
    drive = _make_document('movie', title='Drive')
    click.secho(json.dumps(drive, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Trying to create a BlueRay with *invalid* subtitles...', fg='green')
    try:
        _make_document('blueray', movie_id=drive['_id'], subtitles=['german', 'brasilian'])
    except requests.HTTPError as e:
        click.secho(str(e), fg='red')
        click.secho(json.dumps(e.response.json(), indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Trying to create a BlueRay with *valid* subtitles...', fg='green')
    blueray = _make_document('blueray', movie_id=drive['_id'], subtitles=['de_de', 'pt_br'])
    click.secho(json.dumps(blueray, indent=2, sort_keys=True), fg='yellow')


@demo.command()
def required():
    """Demonstrate *required* property validation"""

    click.secho('*** Trying to create a movie *without* a title...', fg='green')
    try:
        _make_document('movie', title=None)
    except requests.HTTPError as e:
        click.secho(str(e), fg='red')
        click.secho(json.dumps(e.response.json(), indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Creating a movie *with* title...', fg='green')

    leon = _make_document('movie', title='Leon the Professional')
    click.secho(json.dumps(leon, indent=2, sort_keys=True), fg='yellow')


@demo.command()
def unique():
    """Demonstrate *unique* property validation"""

    click.secho('*** Creating User...', fg='green')
    email = 'mclovin-{}@example.net'.format(uuid4().hex)
    mclovin = _make_document('user', email=email, age=21)
    click.secho(json.dumps(mclovin, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Trying to create another user with the same email...', fg='green')
    try:
        _make_document('user', email=email, age=16)
    except requests.HTTPError as e:
        click.secho(str(e), fg='red')
        click.secho(json.dumps(e.response.json(), indent=2, sort_keys=True), fg='yellow')


@demo.command()
def unique_together():
    """Demonstrate *unique_together* property validation"""
    # we'll add a suffix because we can't assume the index to be clean
    suffix = uuid4().hex

    click.secho('*** Creating the first Movie of a series...', fg='green')
    gf1 = _make_document(
        'movie',
        title='The Godfather',
        series_title='The Godfather Trilogy - %s' % suffix,
        series_part=1
    )
    click.secho(json.dumps(gf1, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Creating the second Movie of a series...', fg='green')
    gf2 = _make_document(
        'movie',
        title='The Godfather Part II',
        series_title='The Godfather Trilogy - %s' % suffix,
        series_part=2
    )
    click.secho(json.dumps(gf2, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Trying to create the third Movie with duplicated series_part...', fg='green')
    try:
        gf3 = _make_document(
            'movie',
            title='The Godfather Part III',
            series_title='The Godfather Trilogy - %s' % suffix,
            series_part=2
        )
    except requests.HTTPError as e:
        click.secho(str(e), fg='red')
        click.secho(json.dumps(e.response.json(), indent=2, sort_keys=True), fg='yellow')
    else:
        click.secho(json.dumps(gf3, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Trying to create the third Movie with correct series_part...', fg='green')
    gf3 = _make_document(
        'movie',
        title='The Godfather Part III',
        series_title='The Godfather Trilogy - %s' % suffix,
        series_part=3
    )
    click.secho(json.dumps(gf3, indent=2, sort_keys=True), fg='yellow')


@demo.command()
def check_geolocation():
    address = '2121 Avenue of the Stars #120'

    click.secho('*** Resolving address \'{}\'...'.format(address), fg='green')
    matches = _geocode_address(address)
    click.secho(json.dumps(matches, indent=2, sort_keys=True), fg='yellow')

    match = matches.pop()

    click.secho('*** Creating a user with a home...', fg='green')
    mcclane = _make_document(
        'user',
        email='mcclane-{}@example.net'.format(uuid4().hex),
        age=33,
        place_of_residence={
            'postal_address': match['formatted_address'],
            'geo_point': '{}, {}'.format(match['lat'], match['lon']),
            'administrative_areas': match['administrative_areas'],
        }
    )
    click.secho(json.dumps(mcclane, indent=2, sort_keys=True), fg='yellow')


@demo.command()
def log_access():
    user = _make_document(
        'user',
        email='mcclane-{}@example.net'.format(uuid4().hex),
        age=33
    )

    click.secho('*** Renting a movie...', fg='green')
    rental = _make_document(
        'rental',
        rented_by=user['_id'],
        rented_on='1988-07-20 19:55',
        return_before='1990-07-04 20:00',
    )
    click.secho(json.dumps(rental, indent=2, sort_keys=True), fg='yellow')

    click.secho('*** Waiting for you to watch the movie...', fg='green')
    sleep(1)

    click.secho('*** Extending the rental...', fg='green')
    rental = _update_document(
        'rental',
        id=rental['_id'],
        rented_by=rental['rented_by'],
        rented_on=rental['rented_on'],
        return_before='1995-05-19 20:00',
    )
    click.secho(json.dumps(rental, indent=2, sort_keys=True), fg='yellow')


@demo.command()
@click.pass_context
def all(ctx):
    """ Run all demonstrations, alphabetically"""
    ctx.forward(check_geolocation)
    ctx.forward(enum)
    ctx.forward(file_upload)
    ctx.forward(fill_from_fkey)
    ctx.forward(include_parents)
    ctx.forward(log_access)
    ctx.forward(minmax)
    ctx.forward(regex)
    ctx.forward(required)
    ctx.forward(unique)
    ctx.forward(unique_together)


if __name__ == '__main__':
    demo(obj={})

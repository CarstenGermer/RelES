RelES
=====

### What is RelES?
RelES is a system written in Python that exposes a RESTlike API to Elasticsearch with additional functionality.
Similar to Elasticsearch being built on top of Lucene® to enhance and add functionality, RelES is built on top of Elasticsearch.

* Adds relational 1 to N foreign key fields between any data objects (RelESfk).
* Data objects related through RelESfk can be denormalized upon query.
* Data from data objects related through RelESfk can be automatically denormalized on write.
  * To take advantage of searches in single types.
  * Allows for a strict category system that is full-text searchable.
* Access rights for customers, groups and users are enforced.
  * Access rights are handled inexpensively and fast through naming of aliases.
* Storage of information about customers' API accesses for accounting.
* Administrative fields (created, changed, customer, editor) can be defined and are automatically maintained.
* Fields can be defined to be "unique" and multiple fields to be "unique together"
* A history of changes to objects is stored in and is accessible from PostgreSQL through the API.
* Field types and logic to handle upload and retrieval of files through the API.
* Based on geolocations and third party API providers, adresses can be verified on write.
* The API provides an endpoint to third party API providers to look up adresses and their geolocations.
* Endpoints and data models are defined via Swagger definitions.
* API blocks potentially harmful calls, commands and fieldnames to Elasticsearch.
* The possibilities of Elasticsearch search are preserved, as far as possible.
* The underlying Elasticsearch can still be accessed and used directly.

_(Elasticsearch is a trademark of Elasticsearch BV, registered in the U.S. and in other countries.)_

### Why RelES?
For a central content storage and retrieval system we were looking for a solution that allows for some relational as well as some additional automated functionality with the ability to handle access rights and accounting for multiple customers while at the same time being able to be massively and easily queried by third parties.

Often systems like that are developed as solutions on top of a PostgreSQL database which mirrors active data to an Elasticsearch for massive consumption.

However, with our need to be able to change and expand models quickly and extensively as well as considering recent advancements of Elasticsearch we decided to base the implementation on Elasticsearch first.

### Is RelES fit for production?
At this point RelES has never been tested in a high stress environment.

On top of the disclaimer included in the MIT license (see LICENSE.txt) we encourage anyone to test, use and help with further development of the system but you have been warned.

### Can I use RelES?
Yes. This software is licensed under the short and simple permissive MIT license with conditions only requiring preservation of copyright and license notices (see LICENSE.txt).


Development
-----------

### Installing the requirements

 * After creating a virtualenv
   (e.g.: `$> mkvirtualenv reles -a /path/to/checkout/`)
 * Install the requirements with `make`:

        $> make requirements_dev

### Setting your `PYTHONPATH`
 * If you want to run the code from the checkout, you have to add it to your
   Python path so that absolutely imported modules will be found:

        $> export PYTHONPATH=/path/to/checkout/:$PYTHONPATH

### Running elasticsearch / postgresql
 * [Docker](http://docs.docker.com/engine/installation/)
   is a lightweight solution for our required services
   [elasticsearch](https://hub.docker.com/_/elasticsearch/) and
   [postgresql](https://hub.docker.com/_/postgresql/).

 * We are using docker-compose to manage our containers
   (installed [together with the engine](https://www.docker.com/products/overview)
   or manually via [`pip install --upgrade docker-compose`](https://docs.docker.com/compose/install/)).

 * Run all services:

        $> docker-compose up -d
        Creating reles_elasticsearch_1
        Creating reles_postgresql_1

| Note |
| ---- |
| You might have to run `sysctl -w vm.max_map_count=262144` as a priviledged user on your *host* to prevent errors during bootstrap checks complaining about `max virtual memory areas` being too low. Check [the guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html) for more information.|

 * Your instances are listening on random ports that can be found via
   `docker-compose port`:

        $> docker-compose port elasticsearch 9200
        0.0.0.0:32800
        $> docker-compose port postgresql 5432
        0.0.0.0:32801

 * So you can reach (e.g.) your elasticsearch with (adjust port according to the
   command above):

        $> curl 127.0.0.1:32800
        {
          "name" : "Jimmy Woo",
          "cluster_name" : "elasticsearch",
          "version" : {
            "number" : "2.2.0",
            "build_hash" : "8ff36d139e16f8720f2947ef62c8167a888992fe",
            "build_timestamp" : "2016-01-27T13:32:39Z",
            "build_snapshot" : false,
            "lucene_version" : "5.4.1"
          },
          "tagline" : "You Know, for Search"
        }

 * The next time you run the command, the existing containers will be
   restarted. To get rid of it you have to remove them manually:

        $> docker-compose stop
        Stopping reles_postgresql_1 ... done
        Stopping reles_elasticsearch_1 ... done
        $> docker-compose rm
        Going to remove reles_postgresql_1, reles_elasticsearch_1
        Are you sure? [yN] y
        Removing reles_postgresql_1 ... done
        Removing reles_elasticsearch_1 ... done

## Settings (.ini and .env)

 * The service is configured via the `config/settings.ini` file. The settings can optionally be
   overridden with exported environment variables and a `.env` file in the project root folder
   will also be loaded. The resolution order is: `env variables` over `.env` over `settings.ini`

 * The script `bin/docker2dotenv.py` can be used to automatically pull docker's IP and PORT settings
   for *elasticsearch* and *postgresql* into the `.env` file. This is built into most `make`
   commands as well.

 * RelES authenticates its users against their Google accounts. To be able to
   do so, you need to provide credentials to access Google's API.
   * Login to the [API Manager](https://console.developers.google.com)
   * Create a new project
     * Note `Your project ID`, you will need it later
   * Activate the [People API](https://console.developers.google.com/apis/api/people.googleapis.com/overview)
   * Configure a [product name](https://console.developers.google.com/apis/credentials/consent)
   * Create [OAuth credentials](https://console.developers.google.com/apis/credentials/oauthclient) for the type `Web application`
     * Authorize the callback URL. For development purposes `http://localhost:8080/login/oauth2callback` will work
   * Copy `your client ID`, `your client secret` and the project ID from above into `configs/client_secrets.json`


### Starting the development server

 * To configure your Elasticsearch host, see [Configuration](#configuration).
 * Start the development server:

        $> python manage.py runserver
         * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
         ...

 * Send requests with your favourite `REST` client.


### Running the tests

 * Run the test suites (magically):

        $> make test
        *** Setting up runtime environment...
        *** Make sure to run 'eval $(docker-machine env default)' first if needed ***
        docker-compose up -d
        ...
        *** Running tests...
        py.test tests
        ========================= test session starts =========================
        ...
        collected 226 items

        tests/test_field_references.py ........
        tests/test_swagger_helpers.py .......
        [...]
        ==================== 226 passed in 267.80 seconds =====================

 * Or manually - assuming the environment is setup already:

        $> py.test tests
        ========================= test session starts =========================
        ...
        collected 226 items

        tests/test_field_references.py ........
        tests/test_swagger_helpers.py .......
        [...]
        ==================== 226 passed in 267.80 seconds =====================

<a name='configuration'></a>

Configuration
-------------

The Application is configured via the `configs/setting.ini` file, which is overriden by
*environment variables* and a *.env file* if present.
You can see all possible config variables in `reles/default_config.py`.


Running Commands
----------------

### Using `manage.py`

 * Help for the available commands and their arguments is available directly
  through the `manage.py` script:

        $> python manage.py
        Usage: manage.py [OPTIONS] COMMAND [ARGS]...

        Options:
          --help  Show this message and exit.

        Commands:
          customers      Customer Management Commands
          index
          permissions  Permission Management Commands
          runserver    Runs the Flask development server i.e.
          shell        Runs a Python shell inside Flask application...
          users        User Management Commands

        $> python manage.py runserver --help
        Usage: manage.py runserver [OPTIONS]

          Runs the Flask development server i.e. app.run().

        Options:
          -p, --port INTEGER            Override PORT setting.
          -d, --debug / -D, --no-debug  Override DEBUG setting.
          --help                        Show this message and exit.


### Managing accounts

 * Creating a customer:

        $> ./manage.py customer create prinz
        Creating customer: prinz...
        * customer created: {'name': u'prinz', 'permissions': {}}

 * Granting permissions to a customer

        $> ./manage.py permissions grant prinz library=read library=write
        * granting "read" permission to "prinz" on index "library"
        * alias created: library_prinz_search
        * granting "write" permission to "prinz" on index "library"
        * alias created: library_prinz_index

 * Creating a user:

        $> ./manage.py users create heidi@prinz.de prinz
        Creating user: heidi@prinz.de
        * user created: {'customers': (u'prinz',), email': u'heidi@prinz.de...}


### Uploading files

  * Make sure your customer has permissions on the media index:

        $> ./manage.py permissions grant intosite media=read media=write
        * granting new permissions to "intosite"

        $> ./manage.py permissions list intosite
        Listing customer permissions "<index>=<permission> (<alias exists>)":
        - media=read (True)
        - media=write (True)


  * Get an authentication token for a user associated with that customer

        $> ./manage.py users create rollo@intosite.de intosite
        Creating user: rollo@intosite.de
        * user created: {'email': u'rollo@intosite.de', 'clie...}

        $> ./manage.py users jwt rollo@intosite.de
        eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.e...Q6u21FKUWSt3B4fXsf1IYCrGUhdLBLNQdNOxTXr9-BDdg

  * POST file to file upload endpoint (upload step 1)

        $> curl -v -X POST http://localhost:8080/cdn/files  \
        -F "file=@IMAGE.JPG;type=image/jpeg" \
        -H "Authorization: Bearer eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.e...Q6u21FKUWSt3B4fXsf1IYCrGUhdLBLNQdNOxTXr9-BDdg"
        < HTTP/1.0 201 CREATED
        < Content-Type: application/json
        < Location: http://localhost:8080/cdn/files/70/70135418789b1d18b7f0bb938b057fd10eebc7b7
        < Content-Length: 141
        < Server: Werkzeug/0.11.10 Python/2.7.10
        < Date: Mon, 30 May 2016 15:48:10 GMT
        <
        {
          "mime": "image/jpeg",
          "path": "/70/70135418789b1d18b7f0bb938b057fd10eebc7b7",
          "sha1": "70135418789b1d18b7f0bb938b057fd10eebc7b7"
        }

  * Create Media Object referencing the uploaded image (upload step 2)

        $> curl -X "POST" "http://localhost:8080/media/picture/" \
	    -H "Authorization: Bearer eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.e...Q6u21FKUWSt3B4fXsf1IYCrGUhdLBLNQdNOxTXr9-BDdg" \
	    -H "Content-Type: application/json" \
	    -d "{\"title\":\"my picture\",\"sys_filename\":\"70/70135418789b1d18b7f0bb938b057fd10eebc7b7\"}"


### Usage examples

You can find some usage examples within the repo:

* [`login_client`](examples/login_client/) showcases the authentication flow between a client and the reles (and google)
* [`blockbuster`](examples/blockbuster/) showcases most of our features by setting up the API of a video rental site
* [`modelcheck`](examples/modelcheck) demonstrates the creation of related documents via the API


### Swagger API Specs

Can be retrieved on a per-index basis from the swagger endpoint, which lists the available schemas if no index is given.

    $> curl -v  http://localhost:9999/swagger/
```json
{
  "blockbuster": "/swagger/blockbuster",
  "media": "/swagger/media"
}
```

    $> curl -v  http://localhost:9999/swagger/blockbuster
```json
{
  "swagger": "2.0",
  "consumes": [
    "application/json"
  ],
  "definitions": {
    "movie": "..."
  },
  "paths": {
    "/blockbuster/movie": "..."
  },
  "produces": [
    "application/json"
  ],
  "schemes": [
    "http",
    "https"
  ]
}
```


## Setup

* Create a *Customer*

        $> ./manage.py customers create blockbuster

* Grant permissions for the *blockbuster* and *media* indexes to the customer

        $> ./manage.py permissions grant blockbuster blockbuster=read blockbuster=write media=write media=read

  Note: If some of the indexes don't exist yet, run `$> python api.py` once to have them created.

* Create a *user* attached to the *customer*

        $> ./manage.py users create bbboss@example.net blockbuster

* Create a JWT token for this *user* (needed to run `demo.py` later)

        $> ./manage.py users jwt bbboss@example.net

## Run service

    $> python api.py --help
    Usage: api.py [OPTIONS]

    Options:
      --port INTEGER  Port to listen on (default: 9999)
      --help          Show this message and exit.

The demo api server can be started without any parameters, all "configuration" of the indexes is
done in the `*.yml` schemas.

    $> python api.py
    INFO:root:Application routes:
    INFO:root:Application routes:
    INFO:root:auth.login                                         HEAD,OPTIONS,GET     /login
    INFO:root:auth.oauth2callback                                HEAD,OPTIONS,GET     /oauth2callback
    INFO:root:document_create                                    POST,OPTIONS         /<index>/<doc_type>/
    INFO:root:document_delete                                    OPTIONS,DELETE       /<index>/<doc_type>/<id>
    INFO:root:document_list                                      HEAD,OPTIONS,GET     /<index>/<doc_type>/
    INFO:root:document_retrieve                                  HEAD,OPTIONS,GET     /<index>/<doc_type>/<id>
    INFO:root:document_retrieve_archived                         HEAD,OPTIONS,GET     /<index>/<doc_type>/<id>/_archive
    INFO:root:document_search                                    HEAD,POST,OPTIONS,GET /<index>/<doc_type>/_search
    INFO:root:document_update                                    PUT,OPTIONS          /<index>/<doc_type>/<id>
    INFO:root:download_file                                      HEAD,OPTIONS,GET     /cdn/files/<path:filename>
    INFO:root:static                                             HEAD,OPTIONS,GET     /static/<path:filename>
    INFO:root:swagger_root                                       HEAD,OPTIONS,GET     /swagger/
    INFO:root:swagger_schema                                     HEAD,OPTIONS,GET     /swagger/<index>
    INFO:root:upload_file                                        POST,OPTIONS         /cdn/files/
    INFO:werkzeug: * Running on http://127.0.0.1:9999/ (Press CTRL+C to quit)

# Run demo

The demo consists of several smaller demo commands which can be run on their own, or all of them at
once with the `all` meta command.

    $> python demo.py --help
    Usage: demo.py [OPTIONS] COMMAND [ARGS]...

    Options:
      --jwt TEXT    Json Web Token (JWT) to use  [required]
      --host TEXT   target hostname (default: localhost:9999)
      --index TEXT  target index (default: blockbuster)
      --help        Show this message and exit.

    Commands:
      all              Run all demonstrations, alphabetically
      enum             Demonstrate *enum* property validation
      file_upload      Demonstrate uploading a file and attaching it...
      fill_from_fkey   Demonstrate *fill_from_fkey* document...
      minmax           Demonstrate *minimum/maximum* pattern...
      regex            Demonstrate *regex* pattern validation
      required         Demonstrate *required* property validation
      unique           Demonstrate *unique* property validation
      unique_together  Demonstrate *unique_together* property...

A JWT token is required to run `demo.py`, for brevity it's pulled into an *env variable* below:

    $> export MYJWT = $(./manage.py users jwt bbboss@example.net)
    $> python demo.py --jwt $MYJWT regex
    *** Creating Movie to create a BlueRay for...
    {
      "_id": "AVU6r5JzQ_HBIOPAiIa1",
      "_version": 1,
      "genres": [
        "violence",
        "love",
        "cars"
      ],
      "title": "Drive"
    }
    *** Trying to create a BlueRay with *invalid* subtitles...
    400 Client Error: BAD REQUEST
    {
      "errors": null,
      "message": "u'german' does not match '^[a-z]{2}(_[a-z]{2})?$'"
    }
    *** Trying to create a BlueRay with *valid* subtitles...
    {
      "_id": "AVU6r5K4Q_HBIOPAiIa2",
      "_version": 1,
      "movie": {
        "_id": "AVU6r5JzQ_HBIOPAiIa1",
        "_version": 1,
        "genres": [
          "violence",
          "love",
          "cars"
        ],
        "title": "Drive"
      },
      "movie_id": "AVU6r5JzQ_HBIOPAiIa1",
      "subtitles": [
        "de_de",
        "pt_br"
      ]
}

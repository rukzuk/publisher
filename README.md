# rukzuk publisher

The rukzuk publisher is a Python/Django based API server which takes a website artifact as zip file and pushes it to a remote hosting provider.

Two different publish types exist:

* `internal` the server is under full control of the admin; uses rsync to deploy. Server requires certain setup to work proper
* `external` users configures via rukzuk how the files should be uploaded (FTPS/SFTP) and where.

The `internal` type is not used if it runs inside of the rukzuk container.

## Setup

### Requirements

All requirements can be found in `requirements.txt`.

### Build with docker

```
docker build . -t rz-publisher
```

Run in backgorund with port forwarding to 8000:
```
docker run -d -p 8000:8000 rz-publisher
```

Enter container with shell for debugging / inspection:

```
docker run --rm -t -i rz-publisher:latest /sbin/my_init -- bash -l
```

Based on [github.com/phusion/baseimage-docker](https://github.com/phusion/baseimage-docker)

## Config

### Create Tokens

You need to create JWT (Json Web Token) for both types:

Data for internal:

```json
{
  "type": "internal",
  "instance": ".*",
  "domain": ".*"
}
```

Data for external:

```json
{
  "type": "external",
  "instance": ".*"
}
```

You need to set a secret in the `settings.ini` (also check `settings-dev.ini` if present, it will override the others):

```ini
[publisher]
jwt-secret=A-VERY-LONG-SECRET
```

You can use something like `pwgen 80 1`


Use a tool to generate the JWT, e.g https://jwt.io/#debugger-io 
Enter secret and payload data there.


### Configure rukzuk instance

In the `config.php` of your rukzuk instance you should add (or replace):

```php
  'publisher' => array(
    'type' => 'externalrukzukservice',
    'externalrukzukservice' => array(
      'hosts' => array('http://localhost:8000'),
      'tokens' => array('internal' => '<INTERNAL TOKEN>', 
                        'external' => '<EXTERNAL TOKEN>'),
      'liveHostingDomain' => '{{id}}.example.com',
      'liveHostingDomainProtocol' => 'http://',
    ),
  ),
```


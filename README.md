# Support-Bot (Fork of [Middleman](https://github.com/elokapina/middleman)) 

[![License:Apache2](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Built with nio-template](https://img.shields.io/badge/built%20with-nio--template-brightgreen)](https://github.com/anoadragon453/nio-template)

Ticketing system for Matrix Synapse Element implemented through a matrix bot.

> Support-Bot Features:
- Messaging system features:
  - ✅ Messages to bot are relayed to management room
  - ✅ Rerequests for decryption keys of unencrypted messages
  - ✅ Decryption key forwarding for staff
  - ✅ Support for message types:
    - ✅ Text messages
    - ✅ Media files
    - ✅ Calls
    - ✅ Replies
    - ✅ Reactions
  - ✅ Anonymous replies from staff through bot
  - ✅ Copy messages from management room to ticket room upon ticket creation
  - GRPC endpoints supporting [support-bot-dashboard](https://github.com/murlock1000/support-bot-dashboard) web dashboard
- Support-bot commands:
  - `!message <room ID or alias> <Text to write>` - Sends a message to a room 
  - `!c claim <Ticket index>` - Claim the ticket with specified index (be invited to the ticket room)
  - `!c claimfor <user id> <Ticket index>` - Claim the ticket with specified index (be invited to the ticket room) for a specific user
  - `!c raise <user id> <ticket name>` - Raise a ticket for a user
  - `!c addstaff <user id>` - Add staff with specified name
  - `!c activeticket <user id>` - Get active ticket of specified user
  - `!c close` - Closes the ticket that belongs to the current room (no longer transmits communications to the ticket room)
  - `!c reopen <Ticked Index>` - Reopens the ticket that belongs to the current room
  - `!c opentickets <user id>` - Lists all currently open tickets, or open tickets that are assigned to a specified staff member
  - `!c setupcommunicationsroom <user id>` - Updates the DM between user and bot.
  - `!c chat <user id>` - Create or join an existing chat for a user with a specified name or for the replied to message sender.

## Running
Best used with Docker, find [images on Docker Hub](https://hub.docker.com/r/murlock1000/support_bot).

An example configuration file is provided as `sample.config.yaml`.

Make a copy of that, edit as required and mount it to `/config/config.yaml` on the Docker container with `cp sample.config.yaml config.docker.yaml`

You'll also need to give the container a folder for storing state. Create a folder, ensure
it's writable by the user the container process is running as and mount it to `/data`.

Example:

```bash
cp sample.config.yaml config.yaml
# Edit config.yaml, see the file for details
mkdir data
docker run -v ${PWD}/config.docker.yaml:/config/config.yaml:ro \
    -v ${PWD}/data:/data --name support_bot murlock1000/support_bot
```

## Usage

The configured management room is the room that all messages support_bot receives in other rooms 
will be relayed to.

Normal discussion can happen in the management room. To create a ticket for a user for further communication you can either:

* Reply to the user message with `!raise <Ticket Name>` - a ticket room for that user will be created and staff invited to it, where normal discussion can continue.
* Create a ticket room with `!c raise @user:server <Ticket Name>` - will create a ticket for the specified user.

## Development

## GRPC protobuf generation
Generate protobuf files in proto/ from root directory:
`python -m grpc_tools.protoc -I grpc_server --python_out=. --pyi_out=. --grpc_python_out=. grpc_server/proto/support_bot.proto`

If you need help or want to otherwise chat, jump to `#middleman:elokapina.fi`!

### Dependencies

* Create a Python 3.8+ virtualenv
* Do `pip install -U pip setuptools pip-tools`
* Do `pip-sync`

To update dependencies, do NOT edit `requirements.txt` directly. Any changes go into
`requirements.in` and then you run `pip-compile`. If you want to upgrade existing
non-pinned (in `requirements.in`) dependencies, run `pip-compile --upgrade`, keeping
the ones that you want to update in `requirements.txt` when commiting. See more info
about `pip-tools` at https://github.com/jazzband/pip-tools

### Releasing

* Update `CHANGELOG.md`
* Commit changelog
* Make a tag
* Push the tag
* Make a GitHub release, copy the changelog for the release there
* Build a docker image
  * `docker build -f docker/Dockerfile . -t murlock1000/support_bot:v<version> --no-cache`
  * `docker tag murlock1000/support_bot:v<version> murlock1000/support_bot:latest`
* Push docker images
* Update topic in `#middleman:elokapina.fi`
* Consider announcing on `#thisweekinmatrix:matrix.org` \o/

## License

Apache2
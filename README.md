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

## Getting started

See [SETUP.md](SETUP.md) for how to setup and run the project.

## Usage

The configured management room is the room that all messages support_bot receives in other rooms 
will be relayed to.

Normal discussion can happen in the management room. To create a ticket for a user for further communication you can either:

* Reply to the user message with `!raise <Ticket Name>` - a ticket room for that user will be created and staff invited to it, where normal discussion can continue.
* Create a ticket room with `!c raise @user:server <Ticket Name>` - will create a ticket for the specified user.

## License

Apache2
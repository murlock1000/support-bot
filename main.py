#!/usr/bin/env python3
import asyncio
import sys
from threading import Thread

from support_bot.config import Config
import grpc_server.server

def f(loop:asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
    
try:
    from support_bot import main

    # Read config file

    # A different config file path can be specified as the first command line argument
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "./data/config.yaml"
    config = Config(config_path)

    # Setup two threads for support-bot and grpc server
    main_loop = asyncio.get_event_loop()
    grpc_loop = asyncio.new_event_loop()
    
    print("Starting grpc loop")
    t = Thread(target=f, args=(grpc_loop,))
    t.start()
    
    # Run the main function of the bot
    try:
        print("Starting main loop")
        main_loop.run_until_complete(main.main(config, main_loop, grpc_loop))
    except Exception as e:
        print("Main loop exited: " + str(e))
    finally:
        asyncio.run_coroutine_threadsafe(grpc_server.server.close(grpc_loop), grpc_loop)
        t.join(timeout=3)
except ImportError as e:
    print("Unable to import support_bot.main:", e)

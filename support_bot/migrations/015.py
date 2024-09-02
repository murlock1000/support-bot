# noinspection PyProtectedMember
def migrate(store):

    if store.db_type == "postgres":
        store._execute("""
        CREATE TABLE IF NOT EXISTS ChatsSupportRelation (
            support_id VARCHAR(80) NOT NULL,
            chat_room_id VARCHAR(80) NOT NULL,
            PRIMARY KEY (support_id, chat_room_id),
            CONSTRAINT fk_ChatsSupportRelation_Support_user_id
              FOREIGN KEY (support_id)
              REFERENCES Support (user_id)
              ON DELETE CASCADE
              ON UPDATE CASCADE,
            CONSTRAINT fk_ChatsSupportRelation_Chats_id
              FOREIGN KEY (chat_room_id)
              REFERENCES Chats (chat_room_id)
              ON DELETE CASCADE
              ON UPDATE CASCADE)
        """)
    else:
        store._execute("""
        CREATE TABLE IF NOT EXISTS `ChatsSupportRelation` (
            `support_id` VARCHAR(80) NOT NULL,
            `chat_room_id` VARCHAR(80) NOT NULL,
            PRIMARY KEY (`support_id`, `chat_room_id`),
            CONSTRAINT `fk_ChatsSupportRelation_Support_user_id`
              FOREIGN KEY (`support_id`)
              REFERENCES `Support` (`user_id`)
              ON DELETE CASCADE
              ON UPDATE CASCADE,
            CONSTRAINT `fk_ChatsSupportRelation_Chats_id`
              FOREIGN KEY (`chat_room_id`)
              REFERENCES `Chats` (`id`)
              ON DELETE CASCADE
              ON UPDATE CASCADE)
        """)
        
        

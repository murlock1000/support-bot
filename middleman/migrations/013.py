# noinspection PyProtectedMember
def migrate(store):

    if store.db_type == "postgres":

        store._execute("""
        CREATE TABLE IF NOT EXISTS TicketLabels (
            id SERIAL NOT NULL,
            name VARCHAR(63) NOT NULL,
            description VARCHAR(255),
            hex_color VARCHAR(7) NOT NULL,
            PRIMARY KEY (id))
        """)

        store._execute("""
        CREATE TABLE IF NOT EXISTS TicketsTicketLabelsRelation (
            ticket_label_id INT NOT NULL,
            ticket_id INT NOT NULL,
            PRIMARY KEY (ticket_label_id, ticket_id),
            CONSTRAINT fk_TicketsTicketLabelsRelation_TicketLabels_id
              FOREIGN KEY (ticket_label_id)
              REFERENCES TicketLabels (id)
              ON DELETE CASCADE
              ON UPDATE CASCADE,
            CONSTRAINT fk_TicketsTicketLabelsRelation_Tickets_id
              FOREIGN KEY (ticket_id)
              REFERENCES Tickets (id)
              ON DELETE CASCADE
              ON UPDATE CASCADE)
        """)
    else:
        store._execute("""
        CREATE TABLE IF NOT EXISTS `TicketLabels` (
            PRIMARY KEY (`id`))
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` VARCHAR(63) NOT NULL,
            `description` VARCHAR(255),
            `hex_color` VARCHAR(7) NOT NULL,
        """)

        store._execute("""
        CREATE TABLE IF NOT EXISTS `TicketsTicketLabelsRelation` (
            `ticket_label_id` INT NOT NULL,
            `ticket_id` INT NOT NULL,
            PRIMARY KEY (`ticket_label_id`, `ticket_id`),
            CONSTRAINT `fk_TicketsTicketLabelsRelation_TicketLabels_id`
              FOREIGN KEY (`ticket_label_id`)
              REFERENCES `TicketLabels` (`id`)
              ON DELETE CASCADE
              ON UPDATE CASCADE,
            CONSTRAINT `fk_TicketsTicketLabelsRelation_Tickets_id`
              FOREIGN KEY (`ticket_id`)
              REFERENCES `Tickets` (`id`)
              ON DELETE CASCADE
              ON UPDATE CASCADE)
        """)
        
        

import d816menu

menu = d816menu.D816Menu()


def update():
    if badge.pressed(BUTTON_UP):
        menu.up()
    elif badge.pressed(BUTTON_DOWN):
        menu.down()

    if badge.pressed(BUTTON_A):
        menu.left()
    elif badge.pressed(BUTTON_C):  # Right
        menu.right()

    if badge.pressed(BUTTON_B):  # OK
        menu.ok()

    menu.display()


run(update)

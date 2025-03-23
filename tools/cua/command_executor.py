import asyncio

async def handle_model_action(page, action, socketio):
    """
    Given a computer action (e.g., click, double_click, scroll, etc.),
    execute the corresponding operation on the Playwright page.
    """
    action_type = action.type
    
    try:
        match action_type:
            case "click":
                x, y = action.x, action.y
                button = action.button
                log_message = f"Action: click at ({x}, {y}) with button '{button}'"
                print(log_message)
                socketio.emit('reasoning_update', {
                    "message": log_message
                })
                if button not in ("left", "right"):
                    button = "left"
                await page.mouse.click(x, y, button=button)   

            case "scroll":
                x, y = action.x, action.y
                scroll_x, scroll_y = action.scroll_x, action.scroll_y
                log_message = f"Action: scroll at ({x}, {y}) with offsets (scroll_x={scroll_x}, scroll_y={scroll_y})"
                print(log_message)
                socketio.emit('reasoning_update', {
                    "message": log_message
                })
                await page.mouse.move(x, y)
                await page.evaluate(f"window.scrollBy({scroll_x}, {scroll_y})")

            case "keypress":
                keys = action.keys
                for k in keys:
                    log_message = f"Action: keypress '{k}'"
                    print(log_message)
                    socketio.emit('reasoning_update', {
                        "message": log_message
                    })
                    if k.lower() == "enter":
                        await page.keyboard.press("Enter")
                    elif k.lower() == "space":
                        await page.keyboard.press(" ")
                    else:
                        await page.keyboard.press(k)
            
            case "type":
                text = action.text
                log_message = f"Action: type text: {text}"
                print(log_message)
                socketio.emit('reasoning_update', {
                    "message": log_message
                })
                await page.keyboard.type(text)

            case "double_click":
                x, y = action.x, action.y
                log_message = f"Action: double click at ({x}, {y})"
                print(log_message)
                socketio.emit('reasoning_update', {
                    "message": log_message
                })
                await page.mouse.dblclick(x, y)
            
            case "wait": 
                log_message = f"Action: wait"
                print(log_message)
                socketio.emit('reasoning_update', {
                    "message": log_message
                })
                await asyncio.sleep(2)

            case _:
                log_message = f"Unrecognized action: {action}"
                print(log_message)
                socketio.emit('reasoning_update', {
                    "message": log_message
                })

    except Exception as e:
        log_message = f"Error handling action {action}: {e}"
        print(log_message)
        socketio.emit('reasoning_update', {
            "message": log_message
        })

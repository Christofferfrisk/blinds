import dash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, State
import dash.exceptions
import RPi.GPIO as GPIO
import socket

# Setup GPIO for Raspberry Pi
in1 = 24
in2 = 23
en = 25

GPIO.setmode(GPIO.BCM)
GPIO.setup(in1, GPIO.OUT)
GPIO.setup(in2, GPIO.OUT)
GPIO.setup(en, GPIO.OUT)
GPIO.output(in1, GPIO.LOW)
GPIO.output(in2, GPIO.LOW)
p = GPIO.PWM(en, 1000)
p.start(100)  # Set PWM to 100 for full power


app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])


app.layout = dbc.Container([
    dbc.Row(html.H1("Motor Control Interface", className='text-center mb-4'), justify="center", align="center"),
    dbc.Row(
        dbc.Col(
            dbc.Button("Up", id="button-up", n_clicks=0, color="primary", className="mb-2"), 
            width=6, className="offset-md-3"
        ), 
        justify="center", align="center"
    ),
    dbc.Row(
        dbc.Col(
            dbc.Button("Down", id="button-down", n_clicks=0, color="success", className="mb-2"), 
            width=6, className="offset-md-3"
        ), 
        justify="center", align="center"
    ),
    dbc.Row(
        dbc.Col(
            dbc.Button("STOP", id="button-stop", n_clicks=0, color="danger"), 
            width=6, className="offset-md-3"
        ), 
        justify="center", align="center"
    ),
    html.Div(id="output-state", className='text-center mb-3'),
    html.Div(id="countdown", className='text-center', style={'fontSize': '20px'}),
    dcc.Interval(id="interval-component", interval=10000, n_intervals=0, max_intervals=0),
    dcc.Store(id='last-command', data=None),
    dcc.Interval(id="countdown-timer", interval=1000, n_intervals=0)
], fluid=True, style={"height": "100vh"}, className="d-flex flex-column justify-content-center")



@app.callback(
    Output('countdown', 'children'),
    [Input('countdown-timer', 'n_intervals'),
     Input('interval-component', 'interval')],
    [State('last-command', 'data')]
)
def update_countdown(n_intervals, interval_duration, last_command):
    if last_command:
        remaining_time = max(0, (interval_duration // 1000) - n_intervals)
        if remaining_time > 0:
            return f"Time remaining for '{last_command}': {remaining_time} seconds"
        else:
            return "Motor stopped or awaiting command"
    return "No command issued yet"
    

@app.callback(
    Output('countdown-timer', 'n_intervals'),
    [Input('button-up', 'n_clicks'),
     Input('button-down', 'n_clicks'),
     Input('button-stop', 'n_clicks')]
)
def reset_countdown(up_clicks, down_clicks, stop_clicks):
    # Using callback_context to check which button was pressed
    ctx = dash.callback_context

    if not ctx.triggered:
        # No button has been pressed yet
        return dash.no_update
    else:
        # Any button press should reset the countdown
        return 0

@app.callback(
    [Output('output-state', 'children'),
     Output('interval-component', 'max_intervals'),
     Output('interval-component', 'interval')],  # Adding an output to dynamically change the interval
    [Input('button-up', 'n_clicks'),
     Input('button-down', 'n_clicks')],
    [State('interval-component', 'n_intervals'),
     State('last-command', 'data')]
)
def control_motor(up_clicks, down_clicks, intervals, last_command):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if ctx == "button-up" and last_command != "button-up":
        GPIO.output(in1, GPIO.LOW)
        GPIO.output(in2, GPIO.HIGH)
        return "Motor moving Upward (Backward)", 1, 40000  # Set interval to 20 seconds for "Up"
    elif ctx == "button-down" and last_command != "button-down":
        GPIO.output(in1, GPIO.HIGH)
        GPIO.output(in2, GPIO.LOW)
        return "Motor moving Downward (Forward)", 1, 27000  # Set interval to 10 seconds for "Down"
    return dash.no_update, dash.no_update, dash.no_update  # No update if the same button is pressed consecutively

@app.callback(
    Output('interval-component', 'n_intervals'),
    [Input('interval-component', 'n_intervals'),
     Input('button-stop', 'n_clicks')],
    [State('interval-component', 'n_intervals')]
)
def stop_motor(intervals, stop_clicks, current_intervals):
    ctx = dash.callback_context

    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == 'button-stop' and stop_clicks > 0:
            GPIO.output(in1, GPIO.LOW)
            GPIO.output(in2, GPIO.LOW)
            return 0  # Reset the interval to stop any ongoing or future intervals

        if trigger_id == 'interval-component' and current_intervals == 1:
            GPIO.output(in1, GPIO.LOW)
            GPIO.output(in2, GPIO.LOW)
            return 0  # Reset the interval to prevent further triggers

    return dash.no_update



@app.callback(
    Output('last-command', 'data'),
    [Input('button-up', 'n_clicks'),
     Input('button-down', 'n_clicks')],
    [State('last-command', 'data')]
)
def set_last_command(up_clicks, down_clicks, last_command):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if ctx in ['button-up', 'button-down']:
        return ctx
    return last_command

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == '__main__':
    ip_address = get_ip_address()
    try:
        app.run_server(host=ip_address, port=8050, debug=True)

    finally:
        GPIO.cleanup()
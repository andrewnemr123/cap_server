#ifndef MAIN_MOTOR_DRIVER_H_
#define MAIN_MOTOR_DRIVER_H_


// GPIO Pinout
#define LED_BLINK_PIN 23
#define US_ECHO_PIN 19
#define US_TRIG_PIN 18
#define RIGHT_MOTOR_DIR_PIN 4
#define LEFT_MOTOR_DIR_PIN 0
#define RIGHT_MOTOR_STOP_PIN 2
#define LEFT_MOTOR_STOP_PIN 15

// Levels
#define STOP_ENGAGE 0
#define STOP_DISEN 1
#define DIR_FOWARD 1
#define DIR_BACK 0

// public functions
void pin_config();
void move_forward(int duration_ms);
void move_backward(int duration_ms);
void rotate_left(int duration_ms);
void rotate_right(int duration_ms);
int us_ping();
void task_blink_led(void *arg);


#endif /* MAIN_MOTOR_DRIVER_H_ */

#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <driver/gpio.h>
#include <esp_err.h>
#include "main.h"
#include "motor_driver.h"

void pin_config()
{
    // Motors
    gpio_reset_pin(LEFT_MOTOR_STOP_PIN);
    gpio_set_direction(LEFT_MOTOR_STOP_PIN, GPIO_MODE_OUTPUT);
    gpio_reset_pin(RIGHT_MOTOR_STOP_PIN);
    gpio_set_direction(RIGHT_MOTOR_STOP_PIN, GPIO_MODE_OUTPUT);
    gpio_reset_pin(LEFT_MOTOR_DIR_PIN);
    gpio_set_direction(LEFT_MOTOR_DIR_PIN, GPIO_MODE_OUTPUT);
    gpio_reset_pin(RIGHT_MOTOR_DIR_PIN);
    gpio_set_direction(RIGHT_MOTOR_DIR_PIN, GPIO_MODE_OUTPUT);

    // Ultrasonic sensor
    gpio_reset_pin(US_TRIG_PIN);
    gpio_set_direction(US_TRIG_PIN, GPIO_MODE_OUTPUT);
    gpio_reset_pin(US_ECHO_PIN);
    gpio_set_direction(US_ECHO_PIN, GPIO_MODE_INPUT);

    // LED
    gpio_reset_pin(LED_BLINK_PIN);
    gpio_set_direction(LED_BLINK_PIN, GPIO_MODE_OUTPUT);

    // Default states
    gpio_set_level(LEFT_MOTOR_STOP_PIN, STOP_ENGAGE);
    gpio_set_level(RIGHT_MOTOR_STOP_PIN, STOP_ENGAGE);
    gpio_set_level(LEFT_MOTOR_DIR_PIN, DIR_FOWARD);
    gpio_set_level(RIGHT_MOTOR_DIR_PIN, DIR_FOWARD);
}

// Private helper
void motor_start()
{
    gpio_set_level(LEFT_MOTOR_STOP_PIN, STOP_DISEN);
    gpio_set_level(RIGHT_MOTOR_STOP_PIN, STOP_DISEN);
}

// Private helper
void motor_stop()
{
    gpio_set_level(LEFT_MOTOR_STOP_PIN, STOP_ENGAGE);
    gpio_set_level(RIGHT_MOTOR_STOP_PIN, STOP_ENGAGE);
}

void move_forward(int duration_ms)
{
    motor_start();
    vTaskDelay(duration_ms / portTICK_PERIOD_MS);
    motor_stop();
}

void move_backward(int duration_ms)
{
    motor_stop();
    gpio_set_level(LEFT_MOTOR_DIR_PIN, DIR_BACK);
    gpio_set_level(RIGHT_MOTOR_DIR_PIN, DIR_BACK);
    motor_start();
    vTaskDelay(duration_ms / portTICK_PERIOD_MS);
    motor_stop();
    gpio_set_level(LEFT_MOTOR_DIR_PIN, DIR_FOWARD);
    gpio_set_level(RIGHT_MOTOR_DIR_PIN, DIR_FOWARD);
}

void rotate_left(int duration_ms)
{
    motor_stop();
    gpio_set_level(LEFT_MOTOR_DIR_PIN, DIR_BACK);
    motor_start();
    vTaskDelay(duration_ms / portTICK_PERIOD_MS);
    motor_stop();
    gpio_set_level(LEFT_MOTOR_DIR_PIN, DIR_FOWARD);
}

void rotate_right(int duration_ms)
{
    motor_stop();
    gpio_set_level(RIGHT_MOTOR_DIR_PIN, DIR_BACK);
    motor_start();
    vTaskDelay(duration_ms / portTICK_PERIOD_MS);
    motor_stop();
    gpio_set_level(RIGHT_MOTOR_DIR_PIN, DIR_FOWARD);
}

int us_ping() {
    // TODO: Translate Arduino code 
    // #define SOUND_SPEED 0.034
    // #define CM_TO_INCH 0.393701

    // long duration;
    // float distanceCm;

    // void loop() {
    //     // Clears the trigPin
    //     digitalWrite(trigPin, LOW);
    //     delayMicroseconds(2);
    //     // Sets the trigPin on HIGH state for 10 micro seconds
    //     digitalWrite(trigPin, HIGH);
    //     delayMicroseconds(10);
    //     digitalWrite(trigPin, LOW);
        
    //     // Reads the echoPin, returns the sound wave travel time in microseconds
    //     duration = pulseIn(echoPin, HIGH);
        
    //     // Calculate the distance
    //     distanceCm = duration * SOUND_SPEED/2;
        
    //     delay(1000);
    // }

    return 0;
}

void task_blink_led(void *arg)
{
	int led_state = 0;
	while (true) {
		led_state = !led_state;
		ESP_LOGI(TAG_DRIVER, "Turning the LED %s!", led_state == true ? "ON" : "OFF");
		gpio_set_level(LED_BLINK_PIN, led_state);
		ESP_LOGI(TAG_DRIVER, "Stack High Water Mark %d", uxTaskGetStackHighWaterMark(NULL));  // free bytes left in stack
		vTaskDelay(10000 / portTICK_PERIOD_MS);  // delay ms
	}
}

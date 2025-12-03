#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <driver/gpio.h>
#include <esp_err.h>
#include <esp_timer.h>
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

int us_ping()
{
#define SOUND_SPEED 0.034 // cm/microsecond

    // Clear trigger pin
    gpio_set_level(US_TRIG_PIN, 0);
    esp_rom_delay_us(2);

    // Send 10us pulse
    gpio_set_level(US_TRIG_PIN, 1);
    esp_rom_delay_us(10);
    gpio_set_level(US_TRIG_PIN, 0);

    // Wait for echo pin to go HIGH
    int timeout = 30000; // 30ms timeout
    int count = 0;
    while (gpio_get_level(US_ECHO_PIN) == 0 && count < timeout)
    {
        esp_rom_delay_us(1);
        count++;
    }

    if (count >= timeout)
        return -1; // timeout error

    // Measure pulse width (echo HIGH duration)
    int64_t start_time = esp_timer_get_time();
    count = 0;
    while (gpio_get_level(US_ECHO_PIN) == 1 && count < timeout)
    {
        esp_rom_delay_us(1);
        count++;
    }
    int64_t end_time = esp_timer_get_time();

    if (count >= timeout)
        return -1;

    long duration = (long)(end_time - start_time);

    // Calculate distance in cm
    float distance_cm = duration * SOUND_SPEED / 2.0;

    return (int)distance_cm;
}

void task_blink_led(void *arg)
{
    int led_state = 0;
    while (true)
    {
        led_state = !led_state;
        ESP_LOGI(TAG_DRIVER, "Turning the LED %s!", led_state == true ? "ON" : "OFF");
        gpio_set_level(LED_BLINK_PIN, led_state);
        ESP_LOGI(TAG_DRIVER, "Stack High Water Mark %d", uxTaskGetStackHighWaterMark(NULL)); // free bytes left in stack
        vTaskDelay(10000 / portTICK_PERIOD_MS);                                              // delay ms
    }
}

#include<wiringPi.h>

void initPinHigh()
{
	digitalWrite(27,HIGH);
	
}
void initPinLow()
{
	digitalWrite(27,LOW);
}
void initPin()
{
	wiringPiSetup();
	pinMode(27,OUTPUT);
	pinMode(26,OUTPUT);
	
}
void turnOnTwo(void)
{
	for(;;)
	{
		digitalWrite(26,HIGH);
		delayMicroseconds(150);	/*0.5ms/420*/
		digitalWrite(26,LOW);
		delayMicroseconds(150);
	}
}

void turnOnThree()
{
	unsigned char i;
	for(;;)
	{
		for(i=0;i<224;i++)
		{
			digitalWrite(26,HIGH);
			delayMicroseconds(80);
			delayMicroseconds(80);
			digitalWrite(26,LOW);
			delayMicroseconds(80);
			delayMicroseconds(80);
		}
		digitalWrite(26,LOW);
		delay(75);
	}
}

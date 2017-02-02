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
int main()
{
	initPin();
	initPinLow();
	turnOnTwo();
	return 0;
}

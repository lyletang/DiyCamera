#include<wiringPi.h>
#define S	224	/*112 调试值:75ms */
int turnOnThree(void)
{
	unsigned char i;
	wiringPiSetup();
	pinMode(26,OUTPUT);
	for(;;)
	{
		for(i=0;i<S;i++)
		{
			digitalWrite(26,HIGH);
			delayMicroseconds(80);	/*244调试值:0.33ms*/
			delayMicroseconds(80);	/*244调试值:0.33ms*/
			digitalWrite(26,LOW);
			delayMicroseconds(80);
			delayMicroseconds(80);
		}
		digitalWrite(26,LOW);
		delay(75);	/* 75ms */
	}
	return 0;
}

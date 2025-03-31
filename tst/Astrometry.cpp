
#include "Astrometry.h"
#include <iostream>

// Рассчитывает UVW в [м] для спутника и геоцентра
// Редукция положения источника проходит согласно astSourcePosition
// Вход:
//		1) double a - прямое восхождение источника ICRF в радианах на эпоху J2000(TT)
//		2) double d - склонение источника ICRF в радианах на эпоху J2000(TT)
//		3) double JD - юлианская дата на момент расчёта
//		4) double isz[3] - прямоугольные координаты спутника в [м] в небесной системе координат EME2000 на эпоху J2000(TT)
//			Примечание: это обычные геоцентрические экваториальные координаты спутника
//		5) double uvw[3] - значения UVW в [м]
// Выход:
//		bool - определяет, виден ли источник или нет (с учетом Солнца: наблюдения в той полусфере, где нет Солнца)
//		Расчеты сохраняются в uvw[3]
bool astUVWGeocenterISZ(double a, double d, double JD, double isz[3], double uvw[3]){
	double A, D;
	astSourcePosition(a, d, JD, &A, &D);
	
	double icrf[3];
	astJ2000ToCelestial(JD, icrf, isz);

	uvw[0] = -sin(A) * icrf[0] + cos(A) * icrf[1];
	uvw[1] = -cos(A) * sin(D) * icrf[0] - sin(A) * sin(D) * icrf[1] + cos(D) * icrf[2];
	uvw[2] = cos(A) * cos(D) * icrf[0] + sin(A) * cos(D) * icrf[1] + sin(D) * icrf[2];

	// Координаты Солнца в ICRF
	double PVB[2][3];
	double PVS[2][3];
	astEarthPositionVelocity(JD, PVB, PVS);
	double SunICRF[3];
	for (int i = 0; i < 3; i++)
		SunICRF[i] = -PVS[0][i] * 1.496e11;

	// Прямоугольные координаты источника в ICRF
	double src[3];
	src[0] = cos(D) * cos(A);
	src[1] = cos(D) * sin(A);
	src[2] = sin(D);
	
	// Угол между ММ и Солнцем
	double scalar = 0;
	for (int i = 0; i < 3; i++)
		scalar += (src[i]) * (SunICRF[i] - icrf[i]);
	
	if (scalar <= 0)
	{
		return true;
	}
	else
	{
		return false;
	}
}

// Рассчитывает UVW в [м] для данного телескопа и геоцентра
// Редукция положения источника проходит согласно astSourcePosition
// Для расчета геодезических координат телескопа
//		используется рекомендуемый для РСДБ МАС эллипсоид IERS-2003: a = 6378136.6 [м]; 1/f = 298.25642
// Вход:
//		1) double a - прямое восхождение источника ICRF в радианах на эпоху J2000(TT)
//		2) double d - склонение источника ICRF в радианах на эпоху J2000(TT)
//		3) double JD - юлианская дата на момент расчёта
//		4) double tel[2][3] - прямоугольные координаты в [м] и скорость в [мм/год] телескопа
//				в земной системе координат ITRF на эпоху J2000(TT)
//		5) double h - ограничение минимальной высоты источника над горизонтом в градусах (0 для горизонта)
//		6) double uvw[3] - значения UVW в [м]
// Выход:
//		bool - определяет, виден ли источник или нет, с учетом введенного угла места
bool astUVWGeocenter(double a, double d, double JD, double tel[2][3], double h, double uvw[3]){
	double A, D;
	double geoc[3], icrf[3], src[3];
	astSourcePosition(a, d, JD, &A, &D);
	astTelescopePosition(JD, tel, geoc);
	astTerrestrialToCelestial(JD, icrf, geoc);
	
	uvw[0] = -sin(A) * icrf[0] + cos(A) * icrf[1];
	uvw[1] = -cos(A) * sin(D) * icrf[0] - sin(A) * sin(D) * icrf[1] + cos(D) * icrf[2];
	uvw[2] = cos(A) * cos(D) * icrf[0] + sin(A) * cos(D) * icrf[1] + sin(D) * icrf[2];

	//astEquatorialToCelestial(JD, uvw, uvw);
	//astCelestialToEquatorial(JD, uvw, uvw);

	src[0] = cos(A) * cos(D);
	src[1] = sin(A) * cos(D);
	src[2] = sin(D);

	double ang = astAngleVector(icrf, src);
	if (ang * 57.29577951 + h < 90) return true;
	return false;
}

// Определяет, виден ли источник для данного телескопа в данный момент времени
// Редукция положения источника проходит согласно astSourcePosition
// Для расчета геодезических координат телескопа
//		используется рекомендуемый для РСДБ МАС эллипсоид IERS-2003: a = 6378136.6 [м]; 1/f = 298.25642
// Вход:
//		1) double a - прямое восхождение источника ICRF в радианах на эпоху J2000(TT)
//		2) double d - склонение источника ICRF в радианах на эпоху J2000(TT)
//		3) double JD - юлианская дата на момент расчёта
//		4) double tel[2][3] - прямоугольные координаты в [м] и скорость в [мм/год] телескопа
//				в земной системе координат ITRF на эпоху J2000(TT)
//		5) double h - ограничение минимальной высоты источника над горизонтом в градусах (0 для горизонта)
// Выход:
//		bool - определяет, виден ли источник или нет, с учетом введенного угла места
// Использует:
//		Библиотека IAU SOFA (GST00B)
bool astIsVisible(double a, double d, double JD, double tel[2][3], double h){
	double A, D;
	double geoc[3], geod[3], icrf[3], src[3];
	astSourcePosition(a, d, JD, &A, &D);
	astTelescopePosition(JD, tel, geoc);
	astTerrestrialToCelestial(JD, icrf, geoc);
	astGeocentricToGeodetic(geoc, geod, 1./298.25642, 6378136.6);

	src[0] = cos(A) * cos(D);
	src[1] = sin(A) * cos(D);
	src[2] = sin(D);

	double ang = astAngleVector(icrf, src);
	if (ang * 57.29577951 + h < 90) return true;
	return false;
}

// Рассчитывает положения телескопа в ITRF на заданную эпоху с учетом:
//		1) Собственного движения телескопа
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double tel[2][3] - прямоугольные координаты в [м] и скорость в [м/год] телескопа
//				в земной системе координат ITRF на эпоху J2000(TT)
//		3) double res[3] - прямоугольные координаты в [м] и скорость в [м/год] телескопа на эпоху t
// Выход:
//		Расчеты сохраняются в res[3]
void astTelescopePosition(double JD, double tel[2][3], double res[3]){
	for (int i = 0; i < 3; i++){
		res[i] = tel[0][i] + tel[1][i] * (JD - 2451545.0) / 365.25;
	}
}

// Редукция положения источника (для наблюдателя в геоцентре) с учетом:
//		1) Годичной аберрацией света
//		2) Отклонение в поле Солнца
// Вход:
//		1) double a - прямое восхождение источника ICRF в радианах на эпоху J2000(TT)
//		2) double d - склонение источника ICRF в радианах на эпоху J2000(TT)
//		3) double JD - юлианская дата на момент расчёта
//		4) double * A - прямое восхождение ICRF в радианах на эпоху t
//		5) double * D - склонение ICRF в радианах на эпоху t
// Выход:
//		Расчеты сохраняются в A, D
// Использует:
//		Библиотека IAU SOFA (AB)
void astSourcePosition(double a, double d, double JD, double *A, double *D){
	double pnat[3], pres[3];
	double PVB[2][3], PVH[2][3];
	double s = 0; 
	double v = 0;

	pnat[0] = cos(a) * cos(d);
	pnat[1] = sin(a) * cos(d);
	pnat[2] = sin(d);

	astEarthPositionVelocity(JD, PVB, PVH);
	for (int i = 0; i < 3; i++){
		PVB[1][i] = PVB[1][i] * 5.787037037E-03;
		v = v + PVB[1][i]*PVB[1][i];
		s = s + PVH[0][i]*PVH[0][i];
	}
	s = sqrt(s);
	v = sqrt(1 - v);

	iauAb(pnat, PVB[1], s, v, pres);

	*D = asin(pres[2]);
	*A = atan2(pres[1], pres[0]);
	return;
}

// Переводит геоцентрические прямоугльные координаты в геодезические
// При расчете необходимо знать модель земного эллипсоида, его сжатие и экваториальный радиус
// Для РСДБ наблюдений МАС рекомендует IERS-2003: a = 6378136.6 [м]		1/f = 298.25642
// Вход:
//		1) double geoc[3] - прямоугольные геоцентрические координаты в [м]
//		2) double geod[3] - геодиезические координаты: {широта [рад], долгота [рад], высота над эллипсоидом [м]}
//		3) double f - сжатие эллипсоида
//		4) double R - экваториальный радиус
// Выход:
//		Расчеты сохраняются в geod[3]
void astGeocentricToGeodetic(double geoc[3], double geod[3], double f, double R){
	double eSqr = f * (2 - f);
	double eE = eSqr / (1 - eSqr);

	double Ro = sqrt(geoc[0]*geoc[0] + geoc[1]*geoc[1] + geoc[2]*geoc[2]);
	double r = sqrt(geoc[0]*geoc[0] + geoc[1]*geoc[1]);
	double b = R*(1 - f);
	double B = atan(geoc[2] * (1 + eE * b / Ro) / r);
	double N = R / sqrt(1 - eSqr * sin(B) *sin(B));
	for (int i = 0; i < 100; i++){
		B = atan( (geoc[2] + N * eSqr * sin(B) ) / (r) );
		N = R / sqrt(1 - eSqr * sin(B) *sin(B));
	}
	double H;
	if (cos(B) == 0) H = geoc[2]/sin(B) - N * (1 - eSqr);
	else H = r/cos(B) - N;

	double L;
	L = atan2(geoc[1], geoc[0]);
	
	geod[0] = B;
	geod[1] = L;
	geod[2] = H;
}

// Расчет положения и скорости геоцентра относительно BCRS
// BCRS - барицентрическая система, оси сонаправлены с ICRS
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double PVB[2][3] - прямоугольные координаты в [а.е.] и скорость в [а.е./сутки] на эпоху t
//				относительно барицентра
//		3) double PVH[2][3] - прямоугольные координаты в [а.е.] и скорость в [а.е./сутки] на эпоху t
//				относительно Солнца
// Выход:
//		Расчеты сохраняются в P[3], V[3]
// Использует:
//		Аналитические эфемериды VSOP2000 (Франция) из библиотеки IAU SOFA (EPV00)
void astEarthPositionVelocity(double JD, double PVB[2][3], double PVH[2][3]){
	double pvb[2][3];
	double pvh[2][3];
	iauEpv00(JD, 0., pvh, pvb);
	for (int i = 0; i < 3; i++){
		PVB[0][i] = pvb[0][i];
		PVH[0][i] = pvh[0][i];
		PVB[1][i] = pvb[1][i];
		PVH[1][i] = pvh[1][i];
	}
}

// Переводит из небесной системы (ICRF) координат в земную (ITRF)
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double itrf[3] - прямоугольные земные координаты [м]
// Выход:
//		Расчеты сохраняются в itrf[3]
// Использует:
//		Библиотека IAU SOFA (C2T00B)
void astCelestialToTerrestrial(double JD, double icrf[3], double itrf[3]){
	double RC2T[3][3];
	iauC2t00b(JD, 0, JD, 0, 0, 0, RC2T);
	for (int i = 0; i < 3; i++){
		itrf[i] = 0.;
		for (int j = 0; j < 3; j++)
			itrf[i] += RC2T[i][j] * icrf[j];
	}
}

// Переводит из небесной системы (ICRF) к средним экватору и эклиптике даты  
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double eq[3] - прямоугольные координаты средних экватора и эклиптики даты [м]
// Выход:
//		Расчеты сохраняются в eq[3]
// Использует:
//		Библиотека IAU SOFA (BP00)
void astCelestialToEquatorial(double JD, double icrf[3], double eq[3]){
	double rb[3][3], rp[3][3], rbp[3][3];
	iauBp00(JD, 0.,	rb, rp, rbp);
	astRotate(rbp, icrf, eq);
}

// Переводит из небесной системы (ICRF) к экваториальной системе J2000
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double j2000[3] - прямоугольные координаты экватора и эклиптики эпохи J2000 [м]
// Выход:
//		Расчеты сохраняются в j2000[3]
// Использует:
//		Библиотека IAU SOFA (BP00)
void astCelestialToJ2000(double JD, double icrf[3], double j2000[3]){
	double rb[3][3], rp[3][3], rbp[3][3];
	iauBp00(JD, 0.,	rb, rp, rbp);
	astRotate(rb, icrf, j2000);
}

// Переводит из земной (ITRF) координат в небесную систему (ICRF) 
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double itrf[3] - прямоугольные земные координаты [м]
// Выход:
//		Расчеты сохраняются в icrf[3]
// Использует:
//		Библиотека IAU SOFA (C2T00B)
void astTerrestrialToCelestial(double JD, double icrf[3], double itrf[3]){
	double RC2T[3][3];
	iauC2t00b(JD, 0, JD, 0, 0, 0, RC2T);
	for (int i = 0; i < 3; i++){
		icrf[i] = 0.;
		for (int j = 0; j < 3; j++)
			icrf[i] += RC2T[j][i] * itrf[j];
	}
}

// Переводит из системы среднего эквтора и эклиптики даты к небесной системе (ICRF) 
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double eq[3] - прямоугольные координаты средних экватора и эклиптики даты [м]
// Выход:
//		Расчеты сохраняются в eq[3]
// Использует:
//		Библиотека IAU SOFA (BP00)
void astEquatorialToCelestial(double JD, double eq[3], double icrf[3]){
	double rb[3][3], rp[3][3], rbp[3][3];
	iauBp00(JD, 0.,	rb, rp, rbp);
	astTranspose(rbp);
	astRotate(rbp, icrf, eq);
}

// Переводит из экваториальной системы J2000 к небесной системы (ICRF) 
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double j2000[3] - прямоугольные координаты экватора и эклиптики эпохи J2000 [м]
// Выход:
//		Расчеты сохраняются в icrf[3]
// Использует:
//		Библиотека IAU SOFA (BP00)
void astJ2000ToCelestial(double JD, double icrf[3], double j2000[3]){
	double rb[3][3], rp[3][3], rbp[3][3];
	iauBp00(JD, 0.,	rb, rp, rbp);
	astTranspose(rb);
	astRotate(rb, j2000, icrf);
}

// Возвращает угол между векторами в радианах (векторы должны быть в одной системе координат)
// Вход:
//		1) double m1[3] - вектор 1
//		2) double m2[3] - вектор 2
// Выход:
//		Угол между векторами в радианах
double astAngleVector(double m1[3], double m2[3]){
		double cos = m1[0] * m2[0] + m1[1] * m2[1] + m1[2] * m2[2];
		double sin = sqrt(
			(m1[1] * m2[2] - m1[2] * m2[1])*(m1[1] * m2[2] - m1[2] * m2[1]) +
			(m1[2] * m2[0] - m1[0] * m2[2])*(m1[2] * m2[0] - m1[0] * m2[2]) +
			(m1[0] * m2[1] - m1[1] * m2[0])*(m1[0] * m2[1] - m1[1] * m2[0])
			);
		
		
		return atan2(sin, cos);
	}

// Домножает вектор v[3] на матрицу m[3][3] слева (поворот)
// Вход:
//		1) double m[3][3] - матрица
//		2) double v[3] - вектор
//		3) double res[3] - вектор
// Выход:
//		Расчеты сохраняются в res[3]
void astRotate(double m[3][3], double v[3], double res[3]){
		double t[3];
		for (int i = 0; i < 3; i++)
			t[i] = v[i];

		for (int i = 0; i < 3; i++){
			res[i] = 0.;
			for (int j = 0; j < 3; j++)
				res[i] += m[i][j] * t[j];
		}
	}

// Транспонирует матрицу
// Вход:
//		1) double m[3][3] - матрица
// Выход:
//		Расчеты сохраняются в m[3][3]
void astTranspose(double m[3][3]){
		double a;

		for (int i = 0; i < 3; i++)
			for (int j = i; j < 3; j++){
				a = m[i][j];
				m[i][j] = m[j][i];
				m[j][i] = a;
			}
	}


/*
void main(){
	
	double ef[2][3], jb[2][3], pt[2][3], on[2][3];
	double ra[3];
	double JD = 2456607.4766106;

	double a = 330.680380712*0.0174532925;
	double d = 42.2777721861*0.0174532925;

	for (int i = 0; i < 3; i++){
		ef[1][i] = 0;
		jb[1][i] = 0;
		pt[1][i] = 0;
		on[1][i] = 0;
	}

	ef[0][0] = 4033947.3271;
	ef[0][1] = 486990.7044;
	ef[0][2] = 4900430.9384;
 
	jb[0][0] = 3822846.295;
	jb[0][1] = -153801.603;
	jb[0][2] = 5086286.27;

	pt[0][0] = -1640953.8646;
	pt[0][1] = -5014816.0199;
	pt[0][2] = 3575411.8106;

	on[0][0] = 3370605.8705;
	on[0][1] = 711917.649;
	on[0][2] = 5349830.8518;

	ra[0] = (19./100.*(19298.615113 - 19298.331413) + 19298.331413)*1000;
	ra[1] = (19./100.*(22000.577719 - 21996.342054) + 21996.342054)*1000;
	ra[2] = (19./100.*(22110.508520 - 22109.305715) + 22109.305715)*1000;

	double uvef[3], uvjb[3], uvon[3], uvpt[3], uvra[3];
	
	astUVWGeocenter(a, d, JD, ef, 0, uvef);
	astUVWGeocenter(a, d, JD, jb, 0, uvjb);
	astUVWGeocenter(a, d, JD, on, 0, uvon);
	astUVWGeocenter(a, d, JD, pt, 0, uvpt);
	astUVWGeocenterISZ(a, d, JD, ra, uvra);

	std::cout.precision(12);

	std::cout << "RA - ON:" << std::endl;
	for (int i = 0; i < 3; i++)
		std::cout << -(uvon[i] - uvra[i]) << std::endl;
	
	std::cout << std::endl << "EF - ON:" << std::endl;
	for (int i = 0; i < 3; i++)
		std::cout << -(uvon[i] - uvef[i]) << std::endl;

	std::cout << std::endl << "PT - ON:" << std::endl;
	for (int i = 0; i < 3; i++)
		std::cout << -(uvon[i] - uvpt[i]) << std::endl;
}*/
#ifndef __MY_HEADER_H2__
#define __MY_HEADER_H2__

#include <math.h>
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
bool astUVWGeocenterISZ(double a, double d, double JD, double isz[3], double uvw[3]);

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
bool astUVWGeocenter(double a, double d, double JD, double tel[2][3], double h, double uvw[3]);

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
bool astIsVisible(double a, double d, double JD, double tel[2][3], double h);

// Рассчитывает положения телескопа в ITRF на заданную эпоху с учетом:
//		1) Собственного движения телескопа
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double tel[2][3] - прямоугольные координаты в [м] и скорость в [м/год] телескопа
//				в земной системе координат ITRF на эпоху J2000(TT)
//		3) double res[3] - прямоугольные координаты в [м] и скорость в [м/год] телескопа на эпоху t
// Выход:
//		Расчеты сохраняются в res[3]
void astTelescopePosition(double JD, double tel[2][3], double res[3]);

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
void astSourcePosition(double a, double d, double JD, double *A, double *D);

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
void astGeocentricToGeodetic(double geoc[3], double geod[3], double f, double R);

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
void astEarthPositionVelocity(double JD, double PVB[2][3], double PVH[2][3]);

// Переводит из небесной системы (ICRF) координат в земную (ITRF)
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double itrf[3] - прямоугольные земные координаты [м]
// Выход:
//		Расчеты сохраняются в itrf[3]
// Использует:
//		Библиотека IAU SOFA (C2T00B)
void astCelestialToTerrestrial(double JD, double icrf[3], double itrf[3]);

// Переводит из небесной системы (ICRF) к средним экватору и эклиптике даты  
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double eq[3] - прямоугольные координаты средних экватора и эклиптики даты [м]
// Выход:
//		Расчеты сохраняются в eq[3]
// Использует:
//		Библиотека IAU SOFA (BP00)
void astCelestialToEquatorial(double JD, double icrf[3], double eq[3]);

// Переводит из небесной системы (ICRF) к экваториальной системе J2000
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double j2000[3] - прямоугольные координаты экватора и эклиптики эпохи J2000 [м]
// Выход:
//		Расчеты сохраняются в j2000[3]
// Использует:
//		Библиотека IAU SOFA (BP00)
void astCelestialToJ2000(double JD, double icrf[3], double j2000[3]);

// Переводит из земной (ITRF) координат в небесную систему (ICRF) 
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double itrf[3] - прямоугольные земные координаты [м]
// Выход:
//		Расчеты сохраняются в icrf[3]
// Использует:
//		Библиотека IAU SOFA (C2T00B)
void astTerrestrialToCelestial(double JD, double icrf[3], double itrf[3]);

// Переводит из системы среднего эквтора и эклиптики даты к небесной системе (ICRF) 
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double eq[3] - прямоугольные координаты средних экватора и эклиптики даты [м]
// Выход:
//		Расчеты сохраняются в eq[3]
// Использует:
//		Библиотека IAU SOFA (BP00)
void astEquatorialToCelestial(double JD, double eq[3], double icrf[3]);

// Переводит из экваториальной системы J2000 к небесной системы (ICRF) 
// Вход:
//		1) double JD - юлианская дата на момент расчёта
//		2) double icrf[3] - прямоугольные небесные координаты [м]
//		3) double j2000[3] - прямоугольные координаты экватора и эклиптики эпохи J2000 [м]
// Выход:
//		Расчеты сохраняются в icrf[3]
// Использует:
//		Библиотека IAU SOFA (BP00)
void astJ2000ToCelestial(double JD, double icrf[3], double j2000[3]);

// Возвращает угол между векторами в радианах (векторы должны быть в одной системе координат)
// Вход:
//		1) double m1[3] - вектор 1
//		2) double m2[3] - вектор 2
// Выход:
//		Угол между векторами в радианах
double astAngleVector(double m1[3], double m2[3]);

// Домножает вектор v[3] на матрицу m[3][3] слева (поворот)
// Вход:
//		1) double m[3][3] - матрица
//		2) double v[3] - вектор
//		3) double res[3] - вектор
// Выход:
//		Расчеты сохраняются в res[3]
void astRotate(double m[3][3], double v[3], double res[3]);

// Транспонирует матрицу
// Вход:
//		1) double m[3][3] - матрица
// Выход:
//		Расчеты сохраняются в m[3][3]
void astTranspose(double m[3][3]);

/////////////////////////////////////////////////
// Вспомогательные функции из библиотеки IAU SOFA
/////////////////////////////////////////////////
void iauBpn2xy(double rbpn[3][3], double *x, double *y);
void iauC2ixy(double date1, double date2, double x, double y, double rc2i[3][3]);
void iauC2ixys(double x, double y, double s, double rc2i[3][3]);
void iauPn00(double date1, double date2, double dpsi, double deps, double *epsa, 
			 double rb[3][3], double rp[3][3], double rbp[3][3],
             double rn[3][3], double rbpn[3][3]);

void iauPn00b(double date1, double date2,
              double *dpsi, double *deps, double *epsa,
              double rb[3][3], double rp[3][3], double rbp[3][3],
              double rn[3][3], double rbpn[3][3]);

double iauS00(double date1, double date2, double x, double y);
void iauNut00b(double date1, double date2, double *dpsi, double *deps);
void iauBp00(double date1, double date2,
             double rb[3][3], double rp[3][3], double rbp[3][3]);

double iauObl80(double date1, double date2);
void iauCp(double p[3], double c[3]);
void iauNumat(double epsa, double dpsi, double deps, double rmatn[3][3]);
void iauPr00(double date1, double date2, double *dpsipr, double *depspr);
void iauBi00(double *dpsibi, double *depsbi, double *dra);
int iauEpv00(double date1, double date2, double pvh[2][3], double pvb[2][3]);
void iauPom00(double xp, double yp, double sp, double rpom[3][3]);
double iauEra00(double dj1, double dj2);
void iauC2tcio(double rc2i[3][3], double era, double rpom[3][3],double rc2t[3][3]);
void iauC2i00b(double date1, double date2, double rc2i[3][3]);
double iauAnp(double a);
void iauRy(double theta, double r[3][3]);
void iauRz(double psi, double r[3][3]);
void iauRx(double phi, double r[3][3]);
void iauIr(double r[3][3]);
void iauRxr(double a[3][3], double b[3][3], double atb[3][3]);
void iauPnm00b(double date1, double date2, double rbpn[3][3]);
void iauCr(double r[3][3], double c[3][3]);
void iauC2ibpn(double date1, double date2, double rbpn[3][3], double rc2i[3][3]);
void iauC2t00b(double tta, double ttb, double uta, double utb, double xp, double yp, double rc2t[3][3]);
void iauAb(double pnat[3], double v[3], double s, double bm1, double ppr[3]);
double iauPdp(double a[3], double b[3]);
double iauGst00b(double uta, double utb);
double iauGmst00(double uta, double utb, double tta, double ttb);
double iauGst00b(double uta, double utb);
double iauEe00(double date1, double date2, double epsa, double dpsi);
double iauEect00(double date1, double date2);
double iauEe00b(double date1, double date2);

#endif
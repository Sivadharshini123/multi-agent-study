# Unit 1: Electrostatics (நிலை மின்னியல்)

<!-- page: 1 -->

Electrostatics deals with static electric charges and their interactions.
The fundamental property of electric charge states that like charges repel and unlike charges attract.
The total charge of an isolated system remains conserved. Electric charge is quantized according to the formula:
Q = n * e, where n is an integer and e is the fundamental elementary charge equal to 1.602 x 10^-19 Coulombs (C).

Coulomb's Law states that the electrostatic force of attraction or repulsion between two point charges q1 and q2 separated by a distance r in vacuum is directly proportional to the product of the magnitudes of the charges and inversely proportional to the square of the distance between them.
Mathematical formula:
F = (1 / (4 * pi * epsilon_0)) * (q1 * q2 / r^2)
Here, epsilon_0 is the permittivity of free space, having the value 8.854 x 10^-12 C^2 N^-1 m^-2.
The electrostatic constant k = 1 / (4 * pi * epsilon_0) has a value of approximately 9 x 10^9 N m^2 C^-2.

<!-- page: 2 -->

Electric Field (E) at a point in space is defined as the electrostatic force experienced by a unit positive test charge placed at that point:
E = F / q0
The SI unit of electric field is Newton per Coulomb (N C^-1) or Volt per metre (V m^-1).
Electric field lines originate from positive charges and terminate on negative charges. They never cross each other because if they intersected, there would be two different directions of electric field at the point of intersection, which is physically impossible.

An Electric Dipole (மின் இருமுனை) consists of two equal and opposite point charges (+q and -q) separated by a small distance 2a.
The Electric Dipole Moment vector p is defined as:
p = q * 2a
The direction of the dipole moment is directed from negative charge -q to positive charge +q. The SI unit of dipole moment is Coulomb-metre (C m).

Electric Field due to an Electric Dipole on the Axial Line:
E_axial = (1 / (4 * pi * epsilon_0)) * (2 * p / r^3) (along the dipole axis).
Electric Field due to an Electric Dipole on the Equatorial Plane:
E_equatorial = (1 / (4 * pi * epsilon_0)) * (p / r^3) (opposite to the direction of p).
Notice that for large distances r, the electric field of a dipole falls off as 1 / r^3, which is much faster than the 1 / r^2 dependence of a point charge.

<!-- page: 3 -->

Electric Flux (Phi_E) through an area A is defined as the total number of electric field lines crossing normally through that surface:
Phi_E = integral(E . dA) = E * A * cos(theta)
The SI unit of electric flux is N m^2 C^-1.

Gauss's Law states that the total electric flux linked through any closed surface is equal to 1 / epsilon_0 times the net charge enclosed by the surface:
oint(E . dA) = Q_enclosed / epsilon_0

Applications of Gauss's Law:
1. Electric field due to an infinitely long straight wire carrying uniform linear charge density lambda:
E = lambda / (2 * pi * epsilon_0 * r)
2. Electric field due to an infinite plane sheet of charge with surface charge density sigma:
E = sigma / (2 * epsilon_0)
3. Electric field due to a uniformly charged spherical shell:
Outside the shell (r > R): E = Q / (4 * pi * epsilon_0 * r^2)
On the surface (r = R): E = Q / (4 * pi * epsilon_0 * R^2)
Inside the shell (r < R): E = 0 (electrostatic shielding).

<!-- page: 4 -->

Capacitance and Dielectrics:
A capacitor (மின்தேக்கி) is a device used to store electric charge and electrical energy.
The capacitance C of a capacitor is the ratio of the magnitude of charge Q on either conductor to the potential difference V between them:
C = Q / V
The SI unit of capacitance is Farad (F).

For a parallel plate capacitor with plate area A and separation d:
C = epsilon_0 * A / d
When a dielectric medium of dielectric constant epsilon_r is placed between the plates, the capacitance increases:
C = epsilon * A / d = (epsilon_r * epsilon_0 * A) / d

Energy stored in a capacitor:
The electrostatic potential energy U stored in a charged capacitor is given by:
U = (1/2) * C * V^2 = (1/2) * (Q^2 / C) = (1/2) * Q * V
Electrostatic energy density inside the electric field is u_E = (1/2) * epsilon_0 * E^2.

Van de Graaff Generator:
An electrostatic machine designed by Robert Van de Graaff in 1929 produces high electrostatic potentials of several million volts (10^7 V).
It works on two principles:
1. Electrostatic induction (நிலைமின் தூண்டல்).
2. Action of points or corona discharge (கூர்க்கூனைச் செயல்பாடு).


# Unit 2: Current Electricity (மின்னோட்டவியல்)

<!-- page: 5 -->

Electric Current (I) is defined as the rate of flow of electric charges across any cross-section of a conductor:
I = dQ / dt
The SI unit of current is Ampere (A).

Drift Velocity (v_d) is the average velocity acquired by free electrons inside a conductor under the influence of an applied external electric field:
v_d = - (e * E * tau) / m
Here, e is electronic charge, E is electric field, tau is the relaxation time (average time between two successive collisions), and m is electron mass.
Mobility (mu) is the magnitude of drift velocity per unit electric field:
mu = |v_d| / E = (e * tau) / m. The SI unit of mobility is m^2 V^-1 s^-1.

Microscopic Model of Current:
Current I in a conductor is related to drift velocity by:
I = n * e * A * v_d
Current density J is the current per unit cross-sectional area:
J = I / A = n * e * v_d = sigma * E
This equation J = sigma * E is the microscopic form of Ohm's Law, where sigma is the electrical conductivity of the conductor.

<!-- page: 6 -->

Macroscopic Form of Ohm's Law:
Ohm's Law states that at constant temperature, the steady current I flowing through a conductor is directly proportional to the potential difference V across its ends:
V = I * R
where R is electrical resistance.
Resistance of a uniform conductor of length L and cross-sectional area A is:
R = rho * (L / A)
where rho is electrical resistivity (மின்தடை எண்) with unit Ohm-metre (Ohm m).
Electrical conductivity sigma = 1 / rho with unit Siemens per metre (S m^-1).

Temperature Dependence of Resistance:
For metals, resistivity increases with temperature according to:
rho_T = rho_0 * (1 + alpha * (T - T_0))
where alpha is the temperature coefficient of resistance. For conductors, alpha is positive, whereas for semiconductors and insulators, alpha is negative.

<!-- page: 7 -->

Kirchhoff's Rules (கிர்க்காஃப் விதிகள்):
1. Kirchhoff's First Rule (Current Rule or Junction Rule):
The algebraic sum of the currents meeting at any junction of an electric circuit is zero:
sum(I) = 0.
This rule is based on the law of conservation of electric charge. Current entering a junction is taken as positive, while current leaving is taken as negative.

2. Kirchhoff's Second Rule (Voltage Rule or Loop Rule):
In a closed loop of an electric circuit, the algebraic sum of the products of the current and resistance of each part of the circuit is equal to the algebraic sum of the electromotive forces (EMFs) in that loop:
sum(I * R) = sum(E).
This rule is based on the law of conservation of energy.

Wheatstone's Bridge (வீட்ஸ்டோன் சமனச்சுற்று):
A circuit network of four resistors P, Q, R, and S arranged in a bridge form with a galvanometer G connected between opposite nodes.
Under the balanced condition when no current flows through the galvanometer (I_g = 0):
P / Q = R / S
This formula is widely used to measure unknown resistances with high precision.

Metre Bridge (மீட்டர் சமனச்சுற்று):
Practical application of Wheatstone's bridge using a one-metre uniform resistance wire.
If balancing length is l1, the unknown resistance P is determined by:
P = Q * (l1 / (100 - l1))

Potentiometer (மின்னழுத்தமானி):
A potentiometer measures potential difference without drawing any current from the circuit (ideal voltmeter).
Principle: Potential difference V across length l of a uniform wire is directly proportional to length:
V = phi * l (where phi is potential gradient).
Comparison of EMFs of two primary cells:
xi_1 / xi_2 = l1 / l2


# Unit 3: Magnetism and Magnetic Effects of Current (காந்தவியல்)

<!-- page: 8 -->

Biot-Savart Law (பயோ-சாவர்ட் விதி):
The magnetic field dB at a point due to an infinitesimal current element I dl is:
dB = (mu_0 / (4 * pi)) * (I * dl * sin(theta) / r^2)
where mu_0 is the permeability of free space equal to 4 * pi x 10^-7 T m A^-1.

Magnetic field at the centre of a circular loop carrying current I:
B = (mu_0 * I) / (2 * R)
Along the axis of a circular current loop at distance x:
B = (mu_0 * I * R^2) / (2 * (R^2 + x^2)^(3/2))

Ampere's Circuital Law (ஆம்பியரின் சுற்று விதி):
The line integral of magnetic induction B around any closed path in vacuum is equal to mu_0 times the total steady current enclosed by the loop:
oint(B . dl) = mu_0 * I_enclosed
Magnetic field inside a long tightly wound solenoid carrying current I with n turns per unit length:
B = mu_0 * n * I

<!-- page: 9 -->

Lorentz Force and Moving Charges:
A charge q moving with velocity v in an electric field E and magnetic field B experiences the Lorentz force:
F = q * (E + v x B)
Magnetic Lorentz force alone is:
F_m = q * (v x B) = q * v * B * sin(theta)
Because the magnetic force is perpendicular to velocity at every instant, the magnetic force does zero work on the moving charge. Hence, the kinetic energy and speed of the charged particle remain constant.

Force on a current carrying conductor of length l in magnetic field B:
F = I * (l x B) = I * l * B * sin(theta)

Conversion of Galvanometer into Ammeter and Voltmeter:
1. Conversion to Ammeter:
A galvanometer is converted into an ammeter by connecting a low resistance called a shunt (S) in parallel with the galvanometer:
S = (I_g * R_g) / (I - I_g)
The effective resistance of an ammeter is very low: R_A = (R_g * S) / (R_g + S).
An ideal ammeter has zero resistance.

2. Conversion to Voltmeter:
A galvanometer is converted into a voltmeter by connecting a very high resistance (R_h) in series with the galvanometer:
R_h = (V / I_g) - R_g
The effective resistance of a voltmeter is very high: R_V = R_g + R_h.
An ideal voltmeter has infinite resistance.


# Unit 4: Electromagnetic Induction and Alternating Current (மின்காந்தத் தூண்டல்)

<!-- page: 10 -->

Faraday's Laws of Electromagnetic Induction:
1. Whenever the magnetic flux linked with a closed circuit changes, an electromotive force (EMF) is induced in the circuit. The induced EMF lasts as long as the change in magnetic flux continues.
2. The magnitude of the induced EMF is directly proportional to the time rate of change of magnetic flux linked with the circuit:
xi = - (dPhi_B / dt)
The negative sign represents Lenz's Law, which states that the direction of induced current is always such as to oppose the cause producing it (conservation of energy).

Self-Inductance (தன்னின்தூண்டல்):
The property of a coil to oppose any change in current passing through itself:
Phi_B = L * I, and xi = - L * (dI / dt)
The SI unit of inductance is Henry (H).
Energy stored in an inductor: U_B = (1/2) * L * I^2.

Transformer (மின்மாற்றி):
A transformer is a stationary electrical device used to transfer alternating electrical energy from one circuit to another through mutual induction.
Turns ratio k:
k = V_s / V_p = N_s / N_p = I_p / I_s
For a step-up transformer: k > 1 (N_s > N_p, V_s > V_p, but I_s < I_p).
For a step-down transformer: k < 1 (N_s < N_p, V_s < V_p, but I_s > I_p).
Efficiency of a transformer: eta = (Output Power / Input Power) * 100%.

Series RLC Circuit and Resonance:
Impedance of an RLC series circuit:
Z = sqrt(R^2 + (X_L - X_C)^2)
where inductive reactance X_L = omega * L and capacitive reactance X_C = 1 / (omega * C).
At electrical resonance (X_L = X_C):
Impedance Z = R (minimum), current I is maximum.
Resonant frequency:
f_r = 1 / (2 * pi * sqrt(L * C))
Quality factor Q = (1 / R) * sqrt(L / C).


# Unit 5: Wave Optics and Electromagnetic Waves (அலை ஒளியியல்)

<!-- page: 11 -->

Wave Theory of Light:
Christian Huygens proposed the wave theory of light.
Every point on a primary wavefront acts as a source of secondary spherical wavelets spreading in all directions with the speed of light.
The envelope tangent to these secondary wavelets gives the new wavefront.

Interference of Light:
The superposition of two coherent light waves resulting in modification of intensity in the region of superposition.
In Young's Double Slit Experiment (YDSE):
Condition for constructive interference (Bright fringe): Path difference delta = n * lambda.
Condition for destructive interference (Dark fringe): Path difference delta = (2n - 1) * (lambda / 2).
Fringe width (beta) is the distance between any two consecutive bright or dark fringes:
beta = (lambda * D) / d
where lambda is wavelength, D is distance between slit screen and double slits, and d is distance between the two slits.

Brewster's Law of Polarization:
When unpolarized light strikes a transparent medium at polarizing angle i_p, the reflected ray is completely plane polarized and perpendicular to the refracted ray:
tan(i_p) = mu (refractive index of the medium).


# Unit 6: Semiconductor Electronics (குறைக்கடத்தி எலக்ட்ரானியல்)

<!-- page: 12 -->

Semiconductor Physics:
Energy bands in solids consist of valence band, conduction band, and forbidden energy gap (E_g).
In conductors: bands overlap (E_g = 0).
In insulators: E_g > 3 eV (e.g. Diamond E_g = 5.4 eV).
In semiconductors: 0.2 eV < E_g < 3 eV (Silicon E_g = 1.1 eV, Germanium E_g = 0.7 eV).

p-n Junction Diode:
Formed by fusing p-type and n-type semiconductor crystals.
Diffusion of majority carriers creates a depletion layer (அழிவுப் பகுதி) with a barrier potential (0.7 V for Si, 0.3 V for Ge).
Forward bias: p-region connected to positive terminal, n-region to negative terminal. Depletion width decreases, and current flows easily.
Reverse bias: p-region connected to negative terminal, n-region to positive terminal. Depletion width increases, only microampere reverse saturation current flows.

Rectification (திருத்துதல்):
Conversion of alternating current (AC) into direct current (DC).
1. Half-Wave Rectifier: Uses one diode. Maximum theoretical efficiency is 40.6%.
2. Full-Wave Rectifier: Uses center-tapped transformer with two diodes or a bridge of four diodes. Maximum theoretical efficiency is 81.2%. Ripple frequency is 2 * f.

Zener Diode (ஜேனர் இருமுனையம்):
A heavily doped p-n junction diode designed to operate continuously in the reverse breakdown region without damage.
It is widely used as a Voltage Regulator (மின்னழுத்த சீரமைப்பி) because the voltage across the Zener diode remains constant even when the current through it changes over a wide range.

Logic Gates and Boolean Algebra:
Fundamental logic gates: AND, OR, NOT. Universal gates: NAND and NOR.
De Morgan's First Theorem: (A + B)' = A' . B'
De Morgan's Second Theorem: (A . B)' = A' + B'

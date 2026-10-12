"""
Reed-Solomon (RS) Code Implementation & Finite Field Arithmetic

Author: Nathan Kimutai(tekindet)

This module provides a standalone, zero-dependency implementation of Reed-Solomon
error-correcting codes over Galois Field GF(2^8) using polynomial arithmetic
"""
class RSCodec:
    def __init__(self,n,k):
        self.nsym = 4
        self.n = n

    def berlekamp_massey(self,synds):
        C = GF256Poly([1])
        B = GF256Poly([1])

        m = 1 
        L = 0

        for n in range(len(synds)):
            d = synds[n]
            for i in range(1,L + 1):
                if i < len(C.coeffs):
                    d = GF256.add(d,GF256.mul(C.coeffs[-(i + 1)],synds[n - i]))
            if d == 0:
                m = m + 1
            else:
                T = GF256Poly(list(C.coeffs))
                # C(x) = C(x) + d * B(x) * x^m
                d_B_shifted = B.scale(d).shift(m)
                C = C + d_B_shifted

                if 2 * L <= n:
                    L = n + 1 - L
                    B = T.scale(GF256.inv(d))
                    m = 1
                else:
                    m += 1
        return C

    def encode(self,msg):

        msg_bytes = [ord(c) for c in msg]

        M_x = GF256Poly(msg_bytes)
        G_x = build_generator_poly(self.nsym)

        # x^4 for parity symbols
        shift_factor = GF256Poly([1] + [0] * self.nsym)

        M_shifted = M_x * shift_factor

        Q_x,P_x = M_shifted.divmod(G_x)

        # this is the codeword, this is what we are sending
        # to the receiver
        C_x = M_shifted + P_x

        # todo(test): introduce noise in a channel, also 
        # refactor it so that it is easy to use

        #print(f"Final Codeword C(x):\n{C_x}")

        #Q_verify,R_verify = C_x.divmod(G_x)

        return C_x

    def decode(self,msg):

        R_x = GF256Poly(msg)

        syndromes = []

        for i in range(self.nsym):

            alpha_i = GF256.pow(2,i)

            factor = GF256Poly([1,alpha_i])

            Q_x,P_x = R_x.divmod(factor)

            rem_val = P_x.coeffs[0] if P_x.coeffs else 0
            syndromes.append(rem_val)


        return syndromes

    def correct_errors(self,coeffs):
        """
        Can only correct upto t errors where t = (n - k) / 2
        """
        synds = self.decode(coeffs)

        if all(s == 0 for s in synds):
            print("Syndromes all ZERO -> No errors detected.")
            return list(coeffs)

        print("There are some errors you need to deal with")

        #R_x = GF256Poly(synds)
        lambda_x = self.berlekamp_massey(synds)
        error_pos = self.chien_search(lambda_x,len(coeffs))
        error_mag = self.forney_algorithm(synds,lambda_x,error_pos,len(coeffs))

        corrected = list(coeffs)
        for pos,mag in error_mag.items():
            corrected[pos] = GF256.add(corrected[pos], mag)

        return corrected

    def chien_search(self,x_poly,msg_len):
        error_locations = []
        for i in range(msg_len):
            X_inv = GF256.pow(2,(255 - (msg_len - 1 - i)) % 255)
            res = x_poly.eval(X_inv)
            if res == 0: 
                error_locations.append(i)
        return error_locations

    def forney_algorithm(self,synds,lambda_x,error_positions,msg_len):
        # Omega(x) = S(x) * Lambda(x) mod x^nsym -> keep the lowest nsym powers
        S_x = GF256Poly(list(reversed(synds)))

        A_x_full = S_x * lambda_x 
        A_x = GF256Poly(A_x_full.coeffs[-self.nsym:])

        A_prime = lambda_x.formal_derivative()

        error_magnitudes = {} 

        for pos in error_positions:
            X = GF256.pow(2,(msg_len - 1 - pos) % 255)
            X_inv = GF256.inv(X)

            num = A_x.eval(X_inv)
            den = A_prime.eval(X_inv)

            mag = GF256.mul(X,GF256.div(num,den))
            error_magnitudes[pos] = mag

        return error_magnitudes

    def find_error_locations(self,synds):
        """
        Can only correct upto t errors where t = (n - k) / 2
        """

        # Step 1 : Find the error locator polynomial
        A_x = GF256Poly([1])
        v = len(synds)

        t = len(synds)

        for i in range(t - 1):
            alpha_i = GF256.pow(2,i)

            factor = GF256Poly([1,alpha_i])
            A_x *= factor

        return A_x


def build_generator_poly(nsym):
    G_x = GF256Poly([1])

    for i in range(nsym):

        alpha_i = GF256.pow(2,i)

        factor = GF256Poly([1,alpha_i])

        G_x *= factor

    return G_x

class GF256:
    PRIM = 0x11D

    log = [0] * 256
    exp = [0] * 512

    x = 1

    for i in range(255):
        log[x] = i
        exp[i] = x

        x <<= 1

        if x & 0x100:
            x ^= PRIM

    for i in range(255,512):
        exp[i] = exp[i - 255]

    @classmethod
    def mul(cls,a,b):
        if a == 0 or b == 0: return 0
        return cls.exp[cls.log[a] + cls.log[b]]

    @classmethod
    def inv(cls, a):
        if a == 0: raise ZeroDivisionError("multiplicative inverse of zero is undefined in galois field")
        return cls.exp[255 - cls.log[a]]

    @classmethod
    def add(cls,a,b):
        return a ^ b

    @classmethod
    def sub(cls,a,b):
        return a ^ b

    @classmethod
    def div(cls,a,b):
        if b == 0: raise ZeroDivisionError("division by zero in galois field")
        if a == 0: return 0
        return cls.exp[(cls.log[a] + 255 - cls.log[b]) % 255]

    @classmethod
    def pow(cls,a,power):
        if a == 0:
            return 0 if power != 0 else 1
        return cls.exp[(cls.log[a] * power) % 255]


class GF256Poly:
    def __init__(self,coeffs):

        i = 0
        while i < len(coeffs) - 1 and coeffs[i] == 0:
            i = i + 1
        self.coeffs = coeffs[i:]

    def eval(self,x_val):
        res = 0

        for c in self.coeffs:

            res = GF256.add(GF256.mul(res,x_val),c)

        return res


    def __add__(self,other):
        len_diff = abs(len(self.coeffs) - len(other.coeffs))

        if len(self.coeffs) < len(other.coeffs):
            c1 = [0] * len_diff + self.coeffs
            c2 = other.coeffs
        else:
            c1 = self.coeffs
            c2 = [0] * len_diff + other.coeffs

        res = [GF256.add(a,b) for a,b in zip(c1,c2)]

        return GF256Poly(res)

    def __mul__(self,other):
        # if you multiply two polynomials a and b of 
        # degree N-1 then the result will be of degree
        # 2N - 2 = 2(N-1)
        res = [0] * (len(self.coeffs) + len(other.coeffs) - 1)
        for i,a in enumerate(self.coeffs):
            for j,b in enumerate(other.coeffs):
                res[i + j] = GF256.add(res[i + j],GF256.mul(a,b)) 

        return GF256Poly(res)

    def divmod(self,divisor):
        # return a quotient and a reminder
        out = list(self.coeffs)
        # leading term of divisor
        norm = divisor.coeffs[0]

        for i in range(len(self.coeffs) - len(divisor.coeffs) + 1):
            out[i] = GF256.div(out[i],norm)
            coeff = out[i]

            if coeff != 0:
                for j in range(1,len(divisor.coeffs)):

                    out[i + j] = GF256.add(
                            out[i + j],
                            GF256.mul(divisor.coeffs[j],coeff))

        separator = len(self.coeffs) - len(divisor.coeffs) + 1

        return GF256Poly(out[:separator]),GF256Poly(out[separator:])

    def scale(self, c):
        """Multiplies all coefficients by scalar c."""
        return GF256Poly([GF256.mul(x, c) for x in self.coeffs])

    def shift(self, m):
        """Multiplies polynomial by x^m (appends zeros in descending order)."""
        return GF256Poly(list(self.coeffs) + [0] * m)

    def formal_derivative(self):
        # In GF(2^m) the formal derivative keeps only odd-degree terms.
        n = len(self.coeffs)
        deriv = []
        for i in range(n):
            if (n - 1 - i) % 2 == 1:
                deriv.append(self.coeffs[i])
        return GF256Poly(deriv) if deriv else GF256Poly([0])

    def __repr__(self):

        if self.coeffs == [0]:
            return "0"

        terms = []

        for idx,char in enumerate(self.coeffs):
            if char == 0:
                continue
            deg = len(self.coeffs) - 1

            power = deg - idx

            coeff_str = f"{char}" if(char != 1 or power == 0) else ""

            if power == 0:
                terms.append(f"{char}")
            elif power == 1:
                terms.append(f"{coeff_str}x")
            else:
                terms.append(f"{coeff_str}x^{power}")

        return " + ".join(terms) if terms else "0"

if __name__ == "__main__":
    msg = "This is a test message"

    kodek = RSCodec(8,4)

    C_x = kodek.encode(msg)

    encoded_msg = bytes(C_x.coeffs)

    corrupted_msg = bytearray(encoded_msg)
    corrupted_msg[0] ^= 0xFF

    print(f"Corrupted bytes at pos 0.")

    #syndromes = kodek.decode(corrupted_msg)

    #import pdb; pdb.set_trace()
    corrected_bytes = kodek.correct_errors(corrupted_msg)

    print("corrected ",corrected_bytes)

    msg_len = len(msg)
    decoded_str = "".join(chr(b) for b in corrected_bytes[:msg_len])

    print("Decoded Message : ",decoded_str)

    #res1 = kodek.berlekamp_massey(syndromes)
    #kodek.find_error_locations(res1)

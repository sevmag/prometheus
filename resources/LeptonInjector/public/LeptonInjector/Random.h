#ifndef LI_RANDOM
#define LI_RANDOM

// Ben Smithers
// benjamin.smithers@mavs.uta.edu

// this implements a class to sample numbers just like in an i3 service

#include <random> // mt19937_64, seed_seq, uniform_real_distribution

namespace LeptonInjector {

    class LI_random{
        public:
            LI_random();
            LI_random( unsigned int seed );

            // this naming convention is used to
            double Uniform( double from=0.0, double to=1.0);

            // in case this is set up without a seed! 
            void set_seed(unsigned int new_seed);

        private: 
            // libstdc++'s default_random_engine is minstd_rand0: one cycle of
            // 2^31 - 2 states on which a seed only picks the starting point. A
            // file consumes ~1e5 draws, so seeds whose starting points fall
            // within that distance replay each other's stream and inject the
            // same primaries. mt19937_64 seeded through seed_seq gives every
            // seed an independent, decorrelated stream.
            std::mt19937_64 configuration;
            std::uniform_real_distribution<double> generator;
    };

} //end namespace LeptonInjector

#endif

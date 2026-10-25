#include <LeptonInjector/Random.h>

namespace LeptonInjector{

    namespace {
        std::mt19937_64 engine(unsigned int seed){
            std::seed_seq seq{seed};
            return std::mt19937_64(seq);
        }
    }

    LI_random::LI_random(void){
        // default to boring seed 
        unsigned int seed   = 1;
        configuration       = engine(seed);
        generator           = std::uniform_real_distribution<double>( 0.0, 1.0); 
    }

    LI_random::LI_random( unsigned int seed ){
        configuration       = engine(seed);
        generator           = std::uniform_real_distribution<double>( 0.0, 1.0); 
    }

    // samples a number betwen the two specified values: (from, to)
    //      defaults to ( 0, 1)
    double LI_random::Uniform( double from, double to ){
        if (to < from ){
            throw "'to' should be greater than 'from'";
        }

        double result = (from-to)*(this->generator(configuration)) + to;
        return( result );
    }

    // reconfigures the generator with a new seed 
    void LI_random::set_seed( unsigned int new_seed) {
        this->configuration = engine(new_seed);
    }

} //end namespace LeptonInjector 

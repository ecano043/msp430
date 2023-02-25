MEMORY
{
    ROM (rx):          ORIGIN = 0xfc00, LENGTH = 1020
    RESET_VECTOR (r):  ORIGIN = 0xfffe, LENGTH = 2
}

SECTIONS
{
    .text :
    {
    } > ROM

    reset_vector :
    {
        SHORT(reset)
    } > RESET_VECTOR
}

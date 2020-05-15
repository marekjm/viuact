if [ -t 0 ]; then
    test -r {i}/complete.zsh && . {i}/complete.zsh >/dev/null 2>/dev/null || true
fi

`viuact switch to --default`

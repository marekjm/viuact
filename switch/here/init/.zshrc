#!/usr/bin/env zsh

if [ -f ~/.zshrc ]; then
    . ~/.zshrc
fi

. $VIUACT_SWITCH_PREFIX/init/commonrc

export PS1="(viuact:build) $PS1"

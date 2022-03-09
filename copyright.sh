#!/usr/bin/env bash

# Copyright 2022 Google LLC
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

failed=0

while read -r file; do
	# Skip blank lines (get one if there are no files)
	if [ -z "$file" ]; then
		continue
	fi

	# Skip binary files
	if ! grep -qI . "$file"; then
		continue
	fi

	if [[ $(git log --format=format:%aE "$file" | tail -1) =~ ^(sdgillen@google.com)?$ ]]; then
		if head -3 "$file" | grep -qE 'Copyright 20[0-9]{2} Google LLC'; then
			echo "License header found in $file"
		else
			echo -e "\033[31m\033[1mLicense header not found in $file\033[0m" 1>&2
			((failed++))
		fi
	fi
done <<< "$(
	comm -23 `# Lines only in first (sorted) input file` \
	<(git diff --name-only --diff-filter=A 4b825dc642cb6eb9a060e54bf8d69288fbee4904 | sort) `# Files added` \
	<(git ls-files -ciX .copyrightignore | sort) # Files ignored by .copyrightignore
)"

# Status code is the number of failed files
exit "$failed"

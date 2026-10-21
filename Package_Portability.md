# Package portability

The ZIP contains one unified project: six model/data sections, full-season queue/checkpoints, results, nitrogen source records, technical controls and model inputs. / ZIP, , , .

Machine-specific virtual environments, caches, live logs and nested delivery snapshots are omitted. Rebuild environments with Setup_Windows_Environments.ps1 and its recorded requirements. The complete-season launcher is verified on Windows with Python3.11 for crops and Python3.13 for radiation. Linux needs platform-specific native tools and launcher adaptation.

Native Radiance binaries/support libraries and the official ZIP are retained. The optional unpacked epw2wea.exe is omitted because Windows cannot read that individual file; its original bytes remain inside the official Radiance ZIP. Tianze notebooks read EPW with Python and do not call this converter.

Only completed radiation days and completed crop cases enter running delivery snapshots. Read DELIVERY_STATUS.json before treating a package as final. The same requested ZIP is rebuilt after final table/figure export.

Project data and scientific modules are read within the extracted root. System Python, Windows and native executable staging in the system temporary directory remain normal prerequisites. Original paths in historical provenance reports are records, not current runtime dependencies.
